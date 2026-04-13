use std::process::Child;
use std::sync::Mutex;

use tauri::Manager;

#[allow(dead_code)] // Used only in release builds
const ENGINE_PORT: u16 = 44945;
#[allow(dead_code)]
const ENGINE_ADDR: &str = "127.0.0.1:44945";
const ENGINE_SHUTDOWN_URL: &str = "http://127.0.0.1:44945/system/shutdown";

/// Holds the Python engine child process so we can kill it on exit.
struct EngineProcess(Mutex<Option<Child>>);

// ── Production-only engine management ──────────────────────────────────
// These functions are compiled only in release builds (`tauri build`).
// In dev builds (`tauri dev`), the engine is started by `beforeDevCommand`.

/// Check whether the engine port is already in use.
#[cfg(not(debug_assertions))]
fn port_is_occupied() -> bool {
    std::net::TcpStream::connect(ENGINE_ADDR).is_ok()
}

/// Resolve the engine directory by checking multiple candidate locations.
///
/// Search order:
///   1. Tauri resource directory / engine   (NSIS-installed app)
///   2. Executable's parent directory / engine   (standalone release exe)
///
/// Returns `None` when the engine executable cannot be found anywhere.
#[cfg(not(debug_assertions))]
fn resolve_engine_dir(app: &tauri::App) -> Option<std::path::PathBuf> {
    let exe_name = if cfg!(target_os = "windows") {
        "novem-engine.exe"
    } else {
        "novem-engine"
    };

    // Candidate 1: Tauri resource directory (NSIS-installed location)
    if let Ok(resource_dir) = app.path().resource_dir() {
        let candidate = resource_dir.join("engine");
        log::info!("Checking resource dir: {:?}", candidate);
        if candidate.join(exe_name).exists() {
            log::info!("Engine found in resource dir: {:?}", candidate);
            return Some(candidate);
        }
    }

    // Candidate 2: Next to the executable (standalone release build or
    //              portable deployment where engine/ sits beside the .exe)
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            let candidate = exe_dir.join("engine");
            log::info!("Checking exe dir: {:?}", candidate);
            if candidate.join(exe_name).exists() {
                log::info!("Engine found next to exe: {:?}", candidate);
                return Some(candidate);
            }
        }
    }

    log::error!(
        "Engine executable ({}) not found in any expected location. \
         Ensure the application was installed correctly or the engine/ \
         directory is placed next to the executable.",
        exe_name,
    );
    None
}

/// Start the bundled engine executable as a child process.
#[cfg(not(debug_assertions))]
fn start_engine(
    app: &tauri::App,
    data_dir: &std::path::Path,
    config_dir: &std::path::Path,
) -> Option<Child> {
    use std::process::Command;

    #[cfg(target_os = "windows")]
    use std::os::windows::process::CommandExt;

    let _ = std::fs::create_dir_all(data_dir);
    let _ = std::fs::create_dir_all(config_dir);

    if port_is_occupied() {
        log::error!(
            "Port {} is already in use — cannot start the engine. \
             Close the application occupying that port and restart NOVEM.",
            ENGINE_PORT
        );
        return None;
    }

    let engine_dir = match resolve_engine_dir(app) {
        Some(dir) => dir,
        None => return None,
    };

    let exe_name = if cfg!(target_os = "windows") {
        "novem-engine.exe"
    } else {
        "novem-engine"
    };
    let engine_exe = engine_dir.join(exe_name);

    log::info!(
        "Starting bundled engine: {:?} (data: {:?})",
        engine_exe,
        data_dir,
    );

    let result = {
        let mut cmd = Command::new(&engine_exe);
        cmd.current_dir(&engine_dir)
            .env("NOVEM_DATA_DIR", data_dir)
            .env("NOVEM_CONFIG_DIR", config_dir)
            .env("NOVEM_ENGINE_DIR", &engine_dir)
            .env("NOVEM_ENGINE_PORT", ENGINE_PORT.to_string());

        #[cfg(target_os = "windows")]
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW

        cmd.spawn()
    };

    match result {
        Ok(child) => {
            log::info!("Engine process started (PID: {})", child.id());
            Some(child)
        }
        Err(e) => {
            log::error!("Failed to start engine: {}", e);
            None
        }
    }
}

/// Wait for the engine to accept TCP connections.
#[cfg(not(debug_assertions))]
fn wait_for_engine(timeout_secs: u64) -> bool {
    let start = std::time::Instant::now();
    let timeout = std::time::Duration::from_secs(timeout_secs);
    while start.elapsed() < timeout {
        if std::net::TcpStream::connect(ENGINE_ADDR).is_ok() {
            log::info!(
                "Engine ready after {:.1}s",
                start.elapsed().as_secs_f64()
            );
            return true;
        }
        std::thread::sleep(std::time::Duration::from_millis(300));
    }
    log::error!("Engine did not become ready within {}s", timeout_secs);
    false
}

/// Graceful shutdown: POST /system/shutdown, then force kill on timeout.
fn shutdown_engine(child: &mut Child) {
    let pid = child.id();
    log::info!("Requesting graceful engine shutdown (PID: {})...", pid);

    let _ = std::thread::spawn(|| {
        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(3))
            .build();
        if let Ok(c) = client {
            let _ = c.post(ENGINE_SHUTDOWN_URL).send();
        }
    })
    .join();

    let start = std::time::Instant::now();
    let grace = std::time::Duration::from_secs(5);
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                log::info!("Engine exited gracefully (status: {})", status);
                return;
            }
            Ok(None) if start.elapsed() < grace => {
                std::thread::sleep(std::time::Duration::from_millis(200));
            }
            _ => break,
        }
    }

    log::warn!("Grace period expired, force-killing engine (PID: {})...", pid);
    let _ = child.kill();
    let _ = child.wait();
    log::info!("Engine process terminated");
}

// ── Application entry point ────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            app.handle().plugin(
                tauri_plugin_log::Builder::default()
                    .level(log::LevelFilter::Info)
                    .build(),
            )?;

            // In dev mode, beforeDevCommand (pnpm dev:all) already starts the
            // engine via concurrently. In release, we launch the bundled exe.
            let child = if cfg!(debug_assertions) {
                log::info!("Dev mode: engine managed by beforeDevCommand");
                None
            } else {
                #[cfg(not(debug_assertions))]
                {
                    let app_data = app
                        .path()
                        .app_data_dir()
                        .expect("failed to resolve app data directory");
                    let data_dir = app_data.join("data");
                    let config_dir = app_data.join("config");
                    start_engine(app, &data_dir, &config_dir)
                }
                #[cfg(debug_assertions)]
                { None }
            };
            app.manage(EngineProcess(Mutex::new(child)));

            // Splash → main window transition
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                if cfg!(debug_assertions) {
                    // Dev: just wait for a pleasant splash display
                    std::thread::sleep(std::time::Duration::from_millis(2800));
                } else {
                    // Release: brief splash, then wait for engine readiness
                    std::thread::sleep(std::time::Duration::from_millis(1500));
                    #[cfg(not(debug_assertions))]
                    if !wait_for_engine(30) {
                        log::error!("Proceeding to main window despite engine not being ready");
                    }
                }

                if let Some(splash) = handle.get_webview_window("splash") {
                    let _ = splash.close();
                }
                if let Some(main) = handle.get_webview_window("main") {
                    let _ = main.show();
                    let _ = main.set_focus();
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if window.label() == "main" {
                    let app = window.app_handle();
                    if let Some(state) = app.try_state::<EngineProcess>() {
                        if let Ok(mut guard) = state.0.lock() {
                            if let Some(ref mut child) = *guard {
                                shutdown_engine(child);
                            }
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

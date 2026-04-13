export interface AuthStatus {
  is_setup_complete: boolean;
  user?: UserProfile;
  password_policy?: 'every_start' | 'once_per_session' | 'never';
}

export interface UserProfile {
  id: string;
  name: string;
  email: string | null;
  avatar_seed: string | null;
  avatar_photo: string | null;
  currency: string;
  region: string;
  date_format: string;
  fiscal_year_start: string;
  timezone: string;
  security_question: string | null;
  email_verified: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface SetupRequest {
  name: string;
  email?: string;
  password: string;
  avatar_seed?: string;
  avatar_photo?: string;
  currency?: string;
  region?: string;
  timezone?: string;
  date_format?: string;
  fiscal_year_start?: string;
  security_question?: string;
  security_answer?: string;
}

export interface LoginRequest {
  password: string;
}

export interface LoginResponse {
  token: string;
  user: UserProfile;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ForgotPasswordRequest {
  security_answer: string;
}

export interface ResetPasswordRequest {
  reset_token: string;
  new_password: string;
}

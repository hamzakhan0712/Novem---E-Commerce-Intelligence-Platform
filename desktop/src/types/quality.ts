export interface QualityComponent {
  score: number;
  detail: string;
  issues: string[];
}

export interface QualityScore {
  overall_score: number;
  grade: string;
  components: {
    import_health: QualityComponent;
    completeness: QualityComponent;
    freshness: QualityComponent;
    volume: QualityComponent;
  };
}

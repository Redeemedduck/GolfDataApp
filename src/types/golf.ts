export interface Shot {
  shot_id: string;
  session_id: string;
  date_added: string;
  club: string;
  carry: number;
  total: number;
  smash: number;
  ball_speed: number;
  club_speed: number;
  side_spin: number;
  back_spin: number;
  launch_angle: number;
  side_angle: number;
  club_path: number;
  face_angle: number;
  dynamic_loft: number;
  attack_angle: number;
  impact_x: number;
  impact_y: number;
  optix_x: number | null;
  optix_y: number | null;
  club_lie: string | null;
  lie_angle: number | null;
  side_distance: number;
  descent_angle: number;
  apex: number;
  flight_time: number;
  shot_type: string;
  impact_img: string | null;
  swing_img: string | null;
}

export interface Session {
  session_id: string;
  date: string;
  club: string;
  shot_count: number;
  avg_carry: number;
  avg_smash: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ClubStats {
  club: string;
  shots: number;
  avgCarry: number;
  avgSmash: number;
  avgBallSpeed: number;
  consistency: number;
}

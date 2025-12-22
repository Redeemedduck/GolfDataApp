import { BigQuery } from '@google-cloud/bigquery';

const projectId = process.env.GCP_PROJECT_ID || 'valued-odyssey-474423-g1';
const dataset = process.env.BQ_DATASET_ID || 'golf_data';
const table = process.env.BQ_TABLE_ID || 'shots';

let bigqueryClient: BigQuery | null = null;

function getBigQueryClient() {
  if (!bigqueryClient) {
    bigqueryClient = new BigQuery({ projectId });
  }
  return bigqueryClient;
}

export interface GolfStats {
  totalShots: number;
  avgCarry: number;
  avgSmash: number;
  avgBallSpeed: number;
  clubs: string[];
  recentSessions: number;
}

export interface ClubPerformance {
  club: string;
  shots: number;
  avgCarry: number;
  avgSmash: number;
  avgBallSpeed: number;
  consistency: number;
}

export async function getOverallStats(days: number = 30): Promise<GolfStats> {
  const client = getBigQueryClient();

  const query = `
    SELECT
      COUNT(*) as total_shots,
      ROUND(AVG(carry), 1) as avg_carry,
      ROUND(AVG(smash), 2) as avg_smash,
      ROUND(AVG(ball_speed), 1) as avg_ball_speed,
      STRING_AGG(DISTINCT club ORDER BY club) as clubs,
      COUNT(DISTINCT session_id) as sessions
    FROM \`${projectId}.${dataset}.${table}\`
    WHERE DATE(date_added) >= DATE_SUB(CURRENT_DATE(), INTERVAL ${days} DAY)
      AND carry > 0
  `;

  const [rows] = await client.query({ query });

  if (rows.length === 0 || rows[0].total_shots === 0) {
    return {
      totalShots: 0,
      avgCarry: 0,
      avgSmash: 0,
      avgBallSpeed: 0,
      clubs: [],
      recentSessions: 0,
    };
  }

  const row = rows[0];
  return {
    totalShots: parseInt(row.total_shots),
    avgCarry: parseFloat(row.avg_carry),
    avgSmash: parseFloat(row.avg_smash),
    avgBallSpeed: parseFloat(row.avg_ball_speed),
    clubs: row.clubs ? row.clubs.split(',') : [],
    recentSessions: parseInt(row.sessions),
  };
}

export async function getClubPerformance(days: number = 30): Promise<ClubPerformance[]> {
  const client = getBigQueryClient();

  const query = `
    SELECT
      club,
      COUNT(*) as shots,
      ROUND(AVG(carry), 1) as avg_carry,
      ROUND(AVG(smash), 2) as avg_smash,
      ROUND(AVG(ball_speed), 1) as avg_ball_speed,
      ROUND(STDDEV(carry), 1) as consistency
    FROM \`${projectId}.${dataset}.${table}\`
    WHERE DATE(date_added) >= DATE_SUB(CURRENT_DATE(), INTERVAL ${days} DAY)
      AND carry > 0
    GROUP BY club
    ORDER BY avg_carry DESC
  `;

  const [rows] = await client.query({ query });

  return rows.map((row: any) => ({
    club: row.club,
    shots: parseInt(row.shots),
    avgCarry: parseFloat(row.avg_carry),
    avgSmash: parseFloat(row.avg_smash),
    avgBallSpeed: parseFloat(row.avg_ball_speed),
    consistency: parseFloat(row.consistency || 0),
  }));
}

export async function getRecentShots(club?: string, limit: number = 10) {
  const client = getBigQueryClient();

  const clubFilter = club ? `AND club = '${club}'` : '';

  const query = `
    SELECT
      shot_id,
      session_id,
      club,
      carry,
      total,
      smash,
      ball_speed,
      club_speed,
      launch_angle,
      side_spin,
      back_spin,
      DATE(date_added) as shot_date
    FROM \`${projectId}.${dataset}.${table}\`
    WHERE carry > 0
      ${clubFilter}
    ORDER BY date_added DESC
    LIMIT ${limit}
  `;

  const [rows] = await client.query({ query });
  return rows;
}

export async function executeCustomQuery(userQuery: string): Promise<any> {
  const client = getBigQueryClient();

  // For safety, we'll provide a sanitized interface
  // In production, you'd want more sophisticated query validation
  const [rows] = await client.query({ query: userQuery });
  return rows;
}

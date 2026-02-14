'''
One-time migration: normalize existing club column values.

Usage:
    python -m utils.migrate_club_data --dry-run    # Preview changes
    python -m utils.migrate_club_data              # Execute migration
    python -m utils.migrate_club_data --report     # Summary report only
'''

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automation.naming_conventions import normalize_with_context
import golf_db


def migrate(dry_run=True, report_only=False):
    '''Run the club data migration.'''
    golf_db.init_db()
    conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT club, COUNT(*) as cnt FROM shots GROUP BY club ORDER BY cnt DESC')
    club_counts = cursor.fetchall()

    print(f'\nFound {len(club_counts)} distinct club values\n')

    stats = {
        'already_correct': 0,
        'normalized': 0,
        'club_extracted': 0,
        'set_to_unknown': 0,
        'total_shots': 0,
    }

    changes = []

    for club_value, count in club_counts:
        result = normalize_with_context(club_value)
        new_club = result['club']
        session_type = result['session_type']
        confidence = result['confidence']

        stats['total_shots'] += count

        if new_club == club_value:
            stats['already_correct'] += count
            status = 'OK'
        elif new_club is not None:
            if confidence >= 0.9:
                stats['normalized'] += count
                status = 'NORMALIZE'
            else:
                stats['club_extracted'] += count
                status = 'EXTRACT'
            changes.append((club_value, new_club, session_type, count, status))
        else:
            stats['set_to_unknown'] += count
            status = 'UNKNOWN'
            changes.append((club_value, None, session_type, count, status))

        if not report_only:
            print(f'  [{status:>9}] {str(club_value):>35} -> {str(new_club):>10} '
                  f'(type={session_type}, conf={confidence:.1f}, {count} shots)')

    print(f'\n{"="*60}')
    print('MIGRATION SUMMARY')
    print(f'{"="*60}')
    print(f'  Total shots:           {stats["total_shots"]:>6}')
    print(f'  Already correct:       {stats["already_correct"]:>6}')
    print(f'  Will normalize:        {stats["normalized"]:>6}')
    print(f'  Will extract club:     {stats["club_extracted"]:>6}')
    print(f'  Set to NULL (unknown): {stats["set_to_unknown"]:>6}')
    print(f'  Total changes:         {stats["normalized"] + stats["club_extracted"] + stats["set_to_unknown"]:>6}')

    if dry_run or report_only:
        print('\n  DRY RUN - no changes made.')
        conn.close()
        return stats

    print('\nExecuting migration...')
    changed = 0
    for old_club, new_club, session_type, count, status in changes:
        cursor.execute(
            'UPDATE shots SET original_club_value = club WHERE club = ? AND original_club_value IS NULL',
            (old_club,)
        )
        cursor.execute(
            'UPDATE shots SET club = ? WHERE club = ?',
            (new_club, old_club)
        )
        cursor.execute(
            'INSERT INTO change_log (operation, entity_type, entity_id, details) VALUES (?, ?, ?, ?)',
            ('club_migration', 'shot', str(old_club),
             f'{old_club} -> {new_club} ({count} shots, type={session_type})')
        )
        changed += count

    conn.commit()
    conn.close()
    print(f'  Done. {changed} shots updated.')
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate club column data')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without executing')
    parser.add_argument('--report', action='store_true', help='Summary report only')
    args = parser.parse_args()
    migrate(dry_run=args.dry_run or args.report, report_only=args.report)

"""Database management script."""

import argparse
import os
from pathlib import Path

import alembic.config

def run_migrations(args):
    """Run database migrations."""
    alembic_args = [
        '--raiseerr',
        'upgrade', 'head',
    ]
    alembic.config.main(argv=alembic_args)

def rollback_migrations(args):
    """Rollback database migrations."""
    alembic_args = [
        '--raiseerr',
        'downgrade', '-1',
    ]
    alembic.config.main(argv=alembic_args)

def create_migration(args):
    """Create a new migration."""
    message = args.message or "migration"
    alembic_args = [
        '--raiseerr',
        'revision',
        '--autogenerate',
        '-m', message,
    ]
    alembic.config.main(argv=alembic_args)

def main():
    parser = argparse.ArgumentParser(description="Database management commands")
    subparsers = parser.add_subparsers(dest='command')

    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run migrations')
    migrate_parser.set_defaults(func=run_migrations)

    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migrations')
    rollback_parser.set_defaults(func=rollback_migrations)

    # Create migration command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('--message', '-m', help='Migration message')
    create_parser.set_defaults(func=create_migration)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
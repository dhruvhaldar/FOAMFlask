from app import app, db, SimulationRun

def list_runs():
    with app.app_context():
        # Using db.select for modern SQLAlchemy 2.0 style query
        stmt = db.select(SimulationRun).order_by(SimulationRun.start_time.desc())
        runs = db.session.execute(stmt).scalars().all()

        print(f"Found {len(runs)} simulation runs:")
        print("-" * 100)
        print(f"{'ID':<5} {'Case Name':<30} {'Status':<10} {'Start Time':<20} {'Duration (s)':<12} {'Command'}")
        print("-" * 100)

        for run in runs:
            duration = f"{run.execution_duration:.2f}" if run.execution_duration else "N/A"
            start_str = run.start_time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{run.id:<5} {run.case_name:<30} {run.status:<10} {start_str:<20} {duration:<12} {run.command}")

if __name__ == "__main__":
    list_runs()

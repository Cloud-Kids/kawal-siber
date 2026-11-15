#!/usr/bin/env python3
"""
Verification script for judge interactive mode implementation.
Checks all components without requiring Docker or full deployment.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def check_file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    path = Path(__file__).parent.parent / file_path
    exists = path.exists()
    print(f"{'[OK]' if exists else '[FAIL]'} {file_path}")
    return exists


def check_python_syntax(file_path: str) -> bool:
    """Check Python file syntax."""
    path = Path(__file__).parent.parent / file_path
    if not path.exists():
        print(f"[FAIL] {file_path} - File not found")
        return False
    
    try:
        compile(path.read_text(), file_path, 'exec')
        print(f"[OK] {file_path} - Syntax OK")
        return True
    except SyntaxError as e:
        print(f"[FAIL] {file_path} - Syntax error: {e}")
        return False


def check_environment_variable(env_var: str, expected_value: str = None) -> bool:
    """Check environment variable."""
    value = os.environ.get(env_var)
    if value is None:
        print(f"[WARN] {env_var} - Not set")
        return False
    
    if expected_value and value != expected_value:
        print(f"[FAIL] {env_var} - Expected '{expected_value}', got '{value}'")
        return False
    
    print(f"[OK] {env_var} = {value}")
    return True


def main():
    """Main verification function."""
    print("=" * 60)
    print("KAWAL SIBER - Judge Interactive Mode Verification")
    print("=" * 60)
    print()
    
    # Check required files
    print("[FILE] Checking required files...")
    required_files = [
        "deploy/judge-demo/compose.judge-interactive.yaml",
        "deploy/judge-demo/judge-nginx-interactive.conf",
        "deploy/judge-demo/synthetic-target/Dockerfile",
        "deploy/judge-demo/synthetic-target/nginx.conf",
        "deploy/judge-demo/synthetic-target/html/index.html",
        "backend/app/judge_mode.py",
        "backend/app/integrations/deep_eye/config.py",
        "backend/app/services/web_assessment_service.py",
        "backend/alembic/versions/0009_judge_demo.py",
        "scripts/init-judge-db.sh",
        "backend/tests/test_judge_interactive.py",
        "backend/tests/test_judge_interactive_integration.py",
    ]
    
    all_files_exist = True
    for file_path in required_files:
        if not check_file_exists(file_path):
            all_files_exist = False
    
    print()
    
    # Check Python syntax
    print("[PYTHON] Checking Python syntax...")
    python_files = [
        "backend/app/judge_mode.py",
        "backend/app/integrations/deep_eye/config.py",
        "backend/app/services/web_assessment_service.py",
        "backend/alembic/versions/0009_judge_demo.py",
        "backend/tests/test_judge_interactive.py",
        "backend/tests/test_judge_interactive_integration.py",
    ]
    
    all_syntax_ok = True
    for file_path in python_files:
        if not check_python_syntax(file_path):
            all_syntax_ok = False
    
    print()
    
    # Check environment variables
    print("[CONFIG] Checking environment variables...")
    env_vars = [
        ("KAWAL_JUDGE_MODE", "interactive"),
        ("DATABASE_URL", None),
        ("KAWAL_STORAGE_ROOT", None),
    ]
    
    env_ok = True
    for env_var, expected in env_vars:
        if not check_environment_variable(env_var, expected):
            env_ok = False
    
    print()
    
    # Check Docker Compose file
    print("[DOCKER] Checking Docker Compose configuration...")
    compose_file = Path(__file__).parent.parent / "deploy/judge-demo/compose.judge-interactive.yaml"
    if compose_file.exists():
        try:
            import yaml
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            services = compose_data.get('services', {})
            expected_services = ['judge-proxy', 'judge-backend', 'judge-frontend', 'judge-worker', 'synthetic-target']
            
            for service in expected_services:
                if service in services:
                    print(f"[OK] Service '{service}' configured")
                else:
                    print(f"[FAIL] Service '{service}' missing")
                    env_ok = False
            
            # Check judge mode environment variables
            backend_env = services.get('judge-backend', {}).get('environment', [])
            if any('KAWAL_JUDGE_MODE=interactive' in env for env in backend_env):
                print("[OK] Backend judge mode set to interactive")
            else:
                print("[FAIL] Backend judge mode not set to interactive")
                env_ok = False
                
        except Exception as e:
            print(f"[FAIL] Error parsing compose file: {e}")
            env_ok = False
    else:
        print("[FAIL] Compose file not found")
        env_ok = False
    
    print()
    
    # Summary
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Files exist: {'[OK]' if all_files_exist else '[FAIL]'}")
    print(f"Python syntax: {'[OK]' if all_syntax_ok else '[FAIL]'}")
    print(f"Environment config: {'[OK]' if env_ok else '[FAIL]'}")
    print()
    
    if all_files_exist and all_syntax_ok and env_ok:
        print("[SUCCESS] All checks passed! Implementation is ready for deployment.")
        print()
        print("Next steps:")
        print("1. Install missing dependencies (FastAPI, etc.)")
        print("2. Run database initialization: ./scripts/init-judge-db.sh")
        print("3. Deploy with Docker Compose")
        print("4. Run integration tests")
        return 0
    else:
        print("[WARNING] Some checks failed. Please review the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

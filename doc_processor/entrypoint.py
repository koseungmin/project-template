#!/usr/bin/env python3
"""
Entrypoint script for Prefect doc-processor container.
Replaces bash entrypoint.sh to work without bash in closed network environments.
"""
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Global PIDs and process objects for cleanup
SERVER_PID = None
SERVER_PROCESS = None  # Store subprocess.Popen object for proper cleanup
WORKER_PID = None
WORKER_PROCESS = None

def log(message):
    """Log message with timestamp."""
    from datetime import datetime
    print(f"[{datetime.now().isoformat()}] {message}", flush=True)

def signal_handler(signum, frame):
    """Handle shutdown signals - improved for Kubernetes graceful shutdown.
    
    Key improvements:
    1. Uses subprocess.Popen objects (terminate/kill/wait) instead of just PID
    2. Graceful termination with timeout (30s) before force kill
    3. Proper cleanup of process resources
    4. Better logging for debugging
    """
    log(f"Shutdown signal {signum} received. Stopping Prefect processes...")
    
    # Use subprocess.Popen objects for proper cleanup (better than PID alone)
    processes_to_terminate = []
    
    if WORKER_PROCESS and WORKER_PROCESS.poll() is None:
        log("Terminating worker process...")
        try:
            WORKER_PROCESS.terminate()
            processes_to_terminate.append(("worker", WORKER_PROCESS))
        except Exception as e:
            log(f"Error terminating worker: {e}")
    elif WORKER_PID and is_process_running(WORKER_PID):
        log("Terminating worker process (by PID fallback)...")
        try:
            os.kill(WORKER_PID, signal.SIGTERM)
        except ProcessLookupError:
            pass
    
    if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
        log("Terminating server process...")
        try:
            SERVER_PROCESS.terminate()
            processes_to_terminate.append(("server", SERVER_PROCESS))
        except Exception as e:
            log(f"Error terminating server: {e}")
    elif SERVER_PID and is_process_running(SERVER_PID):
        log("Terminating server process (by PID fallback)...")
        try:
            os.kill(SERVER_PID, signal.SIGTERM)
        except ProcessLookupError:
            pass
    
    # Wait for processes to finish gracefully (max 30 seconds)
    start_time = time.time()
    timeout = 30
    
    for name, proc in processes_to_terminate:
        try:
            log(f"Waiting for {name} to terminate gracefully...")
            remaining_timeout = max(0, timeout - (time.time() - start_time))
            proc.wait(timeout=remaining_timeout)
            log(f"✅ {name} terminated gracefully")
        except subprocess.TimeoutExpired:
            log(f"⚠️ {name} did not terminate in time, sending SIGKILL...")
            try:
                proc.kill()
                proc.wait(timeout=5)
                log(f"✅ {name} force killed")
            except Exception as e:
                log(f"❌ Error killing {name}: {e}")
        except Exception as e:
            log(f"❌ Error waiting for {name}: {e}")
    
    # Also try waitpid for any remaining processes (non-blocking)
    if WORKER_PID:
        try:
            os.waitpid(WORKER_PID, os.WNOHANG)  # Non-blocking
        except (ChildProcessError, ProcessLookupError):
            pass
    if SERVER_PID:
        try:
            os.waitpid(SERVER_PID, os.WNOHANG)  # Non-blocking
        except (ChildProcessError, ProcessLookupError):
            pass
    
    log("All processes terminated. Exiting...")
    sys.exit(0)

def is_process_running(pid):
    """Check if process is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def get_env(key, default):
    """Get environment variable with default."""
    return os.environ.get(key, default)

def ensure_work_pool(work_pool, work_queue):
    """Ensure Prefect work pool exists. Skip check and directly try to create.
    If it already exists, the create command will fail gracefully."""
    if not work_pool:
        return
    
    # First, verify Prefect CLI can connect to server
    log(f"Verifying Prefect CLI connection before work pool operations...")
    log(f"PREFECT_API_URL: {os.environ.get('PREFECT_API_URL', 'NOT SET')}")
    
    # Try both 'prefect' and 'python3 -m prefect'
    test_commands = [
        ["prefect", "work-pool", "ls"],
        ["python3", "-m", "prefect", "work-pool", "ls"]
    ]
    
    cli_works = False
    for test_cmd in test_commands:
        log(f"Testing CLI command: {' '.join(test_cmd)}")
        try:
            test_result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=15,
                env=os.environ.copy()
            )
            log(f"Prefect CLI test: returncode={test_result.returncode}")
            if test_result.returncode == 0:
                log(f"✅ Prefect CLI connection successful!")
                log(f"Output: {test_result.stdout[:200]}")
                cli_works = True
                break
            else:
                log(f"⚠️  Command failed with returncode {test_result.returncode}")
                log(f"stderr: {test_result.stderr[:300] if test_result.stderr else 'None'}")
                log(f"stdout: {test_result.stdout[:300] if test_result.stdout else 'None'}")
        except subprocess.TimeoutExpired:
            log(f"⚠️  CLI test timed out after 15 seconds - server may not be responding!")
        except Exception as e:
            log(f"⚠️  CLI test failed: {e}")
    
    if not cli_works:
        log(f"WARNING: Prefect CLI cannot connect to server! Skipping work pool operations.")
        log(f"This might be normal if server is still starting up. UI should still work.")
        return  # Skip work pool creation if CLI can't connect
    
    # Don't check - just try to create. If it exists, that's fine.
    log(f"Attempting to create work pool '{work_pool}' (will skip if already exists)...")
    cmd = ["prefect", "work-pool", "create", work_pool, "--type", "process"]
    if work_queue and work_queue != "default":
        cmd.extend(["--default-queue", work_queue])
    
    try:
        log(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            env=os.environ.copy()
        )
        
        if result.returncode == 0:
            log(f"Work pool '{work_pool}' created successfully.")
        else:
            # Check if it already exists - that's fine
            error_output = (result.stderr or result.stdout or "").lower()
            if "already exists" in error_output:
                log(f"Work pool '{work_pool}' already exists. Skipping creation.")
            else:
                log(f"Work pool creation returned code {result.returncode}, but continuing...")
                if result.stderr:
                    log(f"stderr: {result.stderr[:300]}")
                if result.stdout:
                    log(f"stdout: {result.stdout[:300]}")
    except subprocess.TimeoutExpired:
        log(f"Work pool create command timed out after 15 seconds. Assuming it exists or will be created later.")
    except Exception as e:
        log(f"Error creating work pool (continuing anyway): {e}")
    
    log("Work pool ensure completed (continuing regardless of result).")

def wait_for_api(url_base, timeout):
    """Wait for Prefect API to be ready."""
    try:
        health_url = f"http://127.0.0.1:4200{url_base}/health"
        log(f"Waiting for Prefect API at {health_url} (timeout {timeout}s)...")
        start_time = time.time()
        server_exit_logged = False
        
        while True:
            try:
                req = urllib.request.Request(health_url)
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        log("Prefect API is ready.")
                        return True
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
                # Log error occasionally to avoid spam
                elapsed = time.time() - start_time
                if int(elapsed) % 10 == 0:  # Log every 10 seconds
                    log(f"Still waiting for API... (elapsed: {int(elapsed)}s)")
            
            # Check if server process died
            if SERVER_PID and not is_process_running(SERVER_PID):
                if not server_exit_logged:
                    log("Prefect server launcher process exited; continuing to wait for API readiness.")
                    server_exit_logged = True
            
            if time.time() - start_time > timeout:
                log(f"Timed out waiting for Prefect server health after {timeout} seconds.")
                return False
            
            time.sleep(3)
    except Exception as e:
        log(f"Unexpected error in wait_for_api: {e}")
        return False

def main():
    """Main entrypoint."""
    global SERVER_PID, WORKER_PID, WORKER_PROCESS
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get configuration from environment
    prefect_server_host = get_env("PREFECT_SERVER_HOST", "0.0.0.0")
    prefect_server_port = get_env("PREFECT_SERVER_PORT", "4200")
    prefect_api_url = get_env("PREFECT_API_URL", f"http://127.0.0.1:{prefect_server_port}/api")
    prefect_ui_url = get_env("PREFECT_UI_URL", f"http://127.0.0.1:{prefect_server_port}")
    prefect_work_pool = get_env("PREFECT_WORK_POOL", "default")
    prefect_work_queue = get_env("PREFECT_WORK_QUEUE", "default")
    prefect_worker_name = get_env("PREFECT_WORKER_NAME", "doc-processor-worker")
    prefect_worker_limit = get_env("PREFECT_WORKER_LIMIT", "1")
    prefect_prefetch_seconds = get_env("PREFECT_PREFETCH_SECONDS", "1")
    prefect_deploy_args = get_env("PREFECT_DEPLOY_ARGS", "--all")
    prefect_yaml_path = get_env("PREFECT_YAML_PATH", "/app/base/prefect.yaml")
    start_prefect_server = get_env("START_PREFECT_SERVER", "1")
    start_prefect_worker = get_env("START_PREFECT_WORKER", "1")
    run_prefect_deploy = get_env("RUN_PREFECT_DEPLOY", "1")
    prefect_health_timeout = int(get_env("PREFECT_HEALTH_TIMEOUT", "180"))
    prefect_ui_serve_base = get_env("PREFECT_UI_SERVE_BASE", "/scheduler")
    prefect_server_api_base_path = get_env("PREFECT_SERVER_API_BASE_PATH", "/scheduler/api")
    
    # Database configuration for Prefect server
    # Check if PostgreSQL should be used for Prefect server
    use_postgresql = get_env("USE_POSTGRESQL_FOR_PREFECT", "0") == "1"
    
    # If explicitly set, use it directly
    prefect_db_url = get_env("PREFECT_API_DATABASE_CONNECTION_URL", None)
    
    if use_postgresql and not prefect_db_url:
        # Read PostgreSQL connection parameters from environment variables
        postgres_host = get_env("POSTGRES_HOST", get_env("PREFECT_DB_HOST", "localhost"))
        postgres_port = get_env("POSTGRES_PORT", get_env("PREFECT_DB_PORT", "5432"))
        postgres_db = get_env("POSTGRES_DB", get_env("PREFECT_DB_NAME", "prefect"))
        postgres_user = get_env("POSTGRES_USER", get_env("PREFECT_DB_USER", "postgres"))
        postgres_password = get_env("POSTGRES_PASSWORD", get_env("PREFECT_DB_PASSWORD", ""))
        postgres_schema = get_env("POSTGRES_SCHEMA", get_env("PREFECT_DB_SCHEMA", None))
        
        # Construct PostgreSQL URL from individual parameters
        # Prefect requires async driver: use postgresql+asyncpg:// or postgresql+psycopg://
        if postgres_password:
            # Check which async driver to use (default: asyncpg)
            async_driver = get_env("PREFECT_DB_ASYNC_DRIVER", "asyncpg")  # asyncpg or psycopg
            
            # Build base URL
            prefect_db_url = f"postgresql+{async_driver}://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
            
            # Add schema option if specified
            # Note: Prefect/SQLAlchemy에서 schema를 설정하는 방법
            # 1. asyncpg/psycopg는 URL query parameter로 schema를 직접 설정할 수 없음
            # 2. connect_args를 사용해야 하지만 Prefect는 URL만 받음
            # 3. 대안: 연결 후 SET search_path 명령 실행 또는
            #    Prefect 설정 파일에서 connect_args 지정 (Prefect 3.x+)
            # 
            # 현재는 URL에 schema를 포함하지 않고, 
            # 사용자가 Prefect 서버 시작 전에 별도로 schema를 설정하도록 안내
            if postgres_schema:
                log(f"⚠️  Schema '{postgres_schema}' specified, but Prefect does not support schema setting via URL.")
                log(f"   PostgreSQL URL query parameters ('options', 'server_settings') are not supported by asyncpg/psycopg drivers.")
                log(f"   Options to set schema:")
                log(f"   1. Create and use a separate database for Prefect (recommended)")
                log(f"   2. Set search_path manually after Prefect server starts")
                log(f"   3. Use PostgreSQL connection pooler with schema routing")
                log(f"   Using base URL without schema setting: postgresql+{async_driver}://{postgres_user}:***@{postgres_host}:{postgres_port}/{postgres_db}")
                log(f"   To use a specific schema, run: ALTER DATABASE {postgres_db} SET search_path TO {postgres_schema};")
            else:
                log(f"Constructed Prefect database URL from environment variables: postgresql+{async_driver}://{postgres_user}:***@{postgres_host}:{postgres_port}/{postgres_db}")
        else:
            # PostgreSQL을 사용하려고 했지만 password가 없어서 SQLite로 fallback
            # 이 경우만 에러 로그 출력 (의도적인 SQLite 사용이 아님)
            log("USE_POSTGRESQL_FOR_PREFECT=1 but POSTGRES_PASSWORD not set. Falling back to SQLite.")
            use_postgresql = False
    
    # Set environment variables for Prefect
    os.environ["PREFECT_API_URL"] = prefect_api_url
    os.environ["PREFECT_UI_URL"] = prefect_ui_url
    os.environ["PREFECT_UI_SERVE_BASE"] = prefect_ui_serve_base
    os.environ["PREFECT_SERVER_API_BASE_PATH"] = prefect_server_api_base_path
    os.environ["PREFECT_DISABLE_TELEMETRY"] = get_env("PREFECT_DISABLE_TELEMETRY", "1")
    os.environ["PREFECT_LOGGING_LEVEL"] = get_env("PREFECT_LOGGING_LEVEL", "INFO")
    
    # Set Prefect database connection URL if PostgreSQL is enabled
    if use_postgresql and prefect_db_url:
        os.environ["PREFECT_API_DATABASE_CONNECTION_URL"] = prefect_db_url
        log(f"✅ Using PostgreSQL for Prefect database")
    # else: SQLite 사용 시 로그 출력하지 않음 (의도적인 사용일 수 있음)
    
    # Create directories
    prefect_home = get_env("PREFECT_HOME", "/opt/prefect")
    Path(prefect_home).mkdir(parents=True, exist_ok=True)
    Path("/root/.prefect").mkdir(parents=True, exist_ok=True)
    
    # Start Prefect server
    if start_prefect_server == "1":
        log(f"Starting Prefect server on {prefect_server_host}:{prefect_server_port}...")
        log(f"PREFECT_API_URL: {prefect_api_url}")
        log(f"PREFECT_HOME: {get_env('PREFECT_HOME', '/opt/prefect')}")
        
        # Start server with output logging
        def log_server_output(pipe, prefix):
            try:
                for line in iter(pipe.readline, ''):
                    if line:
                        log(f"[Server {prefix}] {line.rstrip()}")
            except Exception as e:
                log(f"Error reading server {prefix}: {e}")
        
        process = subprocess.Popen(
            [
                "prefect", "server", "start",
                "--host", prefect_server_host,
                "--port", prefect_server_port
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
            env=os.environ.copy()
        )
        SERVER_PID = process.pid
        SERVER_PROCESS = process  # Store process object for proper cleanup
        log(f"Prefect server PID: {SERVER_PID}")
        
        # Log server output in real-time
        server_stdout_thread = threading.Thread(target=log_server_output, args=(process.stdout, "stdout"), daemon=True)
        server_stderr_thread = threading.Thread(target=log_server_output, args=(process.stderr, "stderr"), daemon=True)
        server_stdout_thread.start()
        server_stderr_thread.start()
        
        # Wait for API to be ready
        log("Calling wait_for_api...")
        api_ready = wait_for_api(prefect_server_api_base_path, prefect_health_timeout)
        log(f"wait_for_api returned: {api_ready}")
        
        if not api_ready:
            log("Failed to start Prefect server. Exiting...")
            sys.exit(1)
        
        log("Prefect server is ready. Proceeding with work pool and deployment...")
        # Give server a bit more time to fully initialize after health check
        log("Waiting additional 3 seconds for server to fully initialize...")
        time.sleep(3)
        
        # Run comprehensive diagnostic (optional, skip if it causes issues)
        diagnostic_script = Path("/app/base/test_prefect_connection.py")
        if diagnostic_script.exists():
            log("Running Prefect connection diagnostic...")
            try:
                diag_result = subprocess.run(
                    ["python3", str(diagnostic_script)],
                    capture_output=True,
                    text=True,
                    timeout=60,  # Increased timeout for cross-platform builds
                    env=os.environ.copy()
                )
                log(f"Diagnostic output:\n{diag_result.stdout}")
                if diag_result.stderr:
                    log(f"Diagnostic errors:\n{diag_result.stderr}")
            except subprocess.TimeoutExpired:
                log("Diagnostic script timed out, but continuing anyway...")
            except Exception as e:
                log(f"Diagnostic script error (continuing anyway): {e}")
    else:
        log(f"Skipping Prefect server start because START_PREFECT_SERVER={start_prefect_server}")
    
    # Ensure work pool exists (non-blocking)
    if run_prefect_deploy == "1" or start_prefect_worker == "1":
        log("Step 1: Ensuring work pool exists...")
        ensure_work_pool(prefect_work_pool, prefect_work_queue)
        log("Work pool step completed, proceeding to next step...")
    else:
        log("Skipping work pool check (deploy and worker both disabled).")
    
    # Start Prefect worker (before deployment) using base/start_worker.py
    if start_prefect_worker == "1":
        log("Step 2: Starting Prefect worker...")
        log(f"Starting Prefect worker using base/start_worker.py...")
        
        worker_script_path = Path("/app/base/start_worker.py")
        
        # Verify script exists and is readable
        if not worker_script_path.exists():
            log(f"Error: Worker script not found at {worker_script_path}")
            log(f"Current directory: {os.getcwd()}")
            log(f"Listing /app/base contents:")
            base_dir = Path("/app/base")
            if base_dir.exists():
                for item in base_dir.iterdir():
                    log(f"  - {item.name} (is_file: {item.is_file()})")
            raise FileNotFoundError(f"Worker script not found: {worker_script_path}")
        
        log(f"Worker script found: {worker_script_path}")
        log(f"Script is readable: {os.access(worker_script_path, os.R_OK)}")
        log(f"Script size: {worker_script_path.stat().st_size} bytes")
        
        try:
            # Set environment variables for worker script
            worker_env = os.environ.copy()
            worker_env.update({
                "PREFECT_API_URL": prefect_api_url,
                "PREFECT_WORK_POOL": prefect_work_pool,
                "PREFECT_WORK_QUEUE": prefect_work_queue,
                "PREFECT_WORKER_NAME": prefect_worker_name,
                "PREFECT_WORKER_LIMIT": prefect_worker_limit,
                "PREFECT_PREFETCH_SECONDS": prefect_prefetch_seconds,
                "PYTHONUNBUFFERED": "1",  # Ensure unbuffered output
            })
            
            log(f"Executing: python3 {worker_script_path}")
            log(f"Environment: PREFECT_API_URL={prefect_api_url}, PREFECT_WORK_POOL={prefect_work_pool}")
            
            process = subprocess.Popen(
                ["python3", str(worker_script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,  # Unbuffered
                env=worker_env
            )
            WORKER_PID = process.pid
            WORKER_PROCESS = process
            log(f"Prefect worker process started. PID: {WORKER_PID}")
            
            # Check if process is still running immediately
            time.sleep(0.5)
            if is_process_running(WORKER_PID):
                log(f"Worker process {WORKER_PID} is running.")
            else:
                log(f"WARNING: Worker process {WORKER_PID} exited immediately!")
                # Try to read any error output
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    if stdout:
                        log(f"Worker stdout: {stdout}")
                    if stderr:
                        log(f"Worker stderr: {stderr}")
                except:
                    pass
            
            # Worker 출력을 실시간으로 로깅
            def log_worker_output(pipe, prefix):
                try:
                    for line in iter(pipe.readline, ''):
                        if line:
                            log(f"[Worker {prefix}] {line.rstrip()}")
                except Exception as e:
                    log(f"Error reading worker {prefix}: {e}")
            
            stdout_thread = threading.Thread(target=log_worker_output, args=(process.stdout, "stdout"), daemon=True)
            stderr_thread = threading.Thread(target=log_worker_output, args=(process.stderr, "stderr"), daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            
            log("Worker started. Waiting 10 seconds before deployment...")
            time.sleep(10)
            
            # Check process status again
            if is_process_running(WORKER_PID):
                log(f"Worker process {WORKER_PID} is still running after 10 seconds.")
            else:
                log(f"WARNING: Worker process {WORKER_PID} exited during wait!")
            
            log("10 seconds elapsed. Proceeding with deployment...")
        except Exception as e:
            log(f"Error starting Prefect worker: {e}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            raise
    
    # Run Prefect deploy (after worker is started and 10 seconds wait) using base/deploy_pipeline.py
    if run_prefect_deploy == "1":
        log("Step 3: Running Prefect deployment...")
        
        deploy_script_path = Path("/app/base/deploy_pipeline.py")
        
        # Verify script exists
        if not deploy_script_path.exists():
            log(f"Error: Deploy script not found at {deploy_script_path}")
            log(f"Current directory: {os.getcwd()}")
            log(f"Listing /app/base contents:")
            base_dir = Path("/app/base")
            if base_dir.exists():
                for item in base_dir.iterdir():
                    log(f"  - {item.name} (is_file: {item.is_file()})")
            log("Skipping deployment.")
        else:
            log(f"Deploy script found: {deploy_script_path}")
            log(f"Script is readable: {os.access(deploy_script_path, os.R_OK)}")
            
            try:
                # Set environment variables for deploy script
                deploy_env = os.environ.copy()
                deploy_env.update({
                    "PREFECT_API_URL": prefect_api_url,
                    "PREFECT_YAML_PATH": prefect_yaml_path,
                    "PYTHONUNBUFFERED": "1",  # Ensure unbuffered output
                })
                
                log(f"Running deploy script: {deploy_script_path}")
                log(f"Using prefect.yaml path: {prefect_yaml_path}")
                log(f"PREFECT_API_URL: {prefect_api_url}")
                
                # Run with immediate output streaming
                # Execute from /app directory so flow paths resolve correctly
                log("Starting deploy script execution...")
                result = subprocess.run(
                    ["python3", str(deploy_script_path)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd="/app",  # Run from /app so flow paths work
                    env=deploy_env
                )
                
                log("Deploy script execution completed.")
                log(f"Return code: {result.returncode}")
                
                if result.stdout:
                    log(f"Deploy script stdout ({len(result.stdout)} chars):")
                    # Print first 1000 chars, then full if needed
                    if len(result.stdout) > 1000:
                        log(result.stdout[:1000])
                        log(f"... (truncated, total {len(result.stdout)} chars)")
                    else:
                        log(result.stdout)
                
                if result.stderr:
                    log(f"Deploy script stderr ({len(result.stderr)} chars):")
                    if len(result.stderr) > 1000:
                        log(result.stderr[:1000])
                        log(f"... (truncated, total {len(result.stderr)} chars)")
                    else:
                        log(result.stderr)
                
                if result.returncode == 0:
                    log("Prefect deployments registered successfully.")
                else:
                    log(f"Deploy script returned code {result.returncode}, but continuing...")
            except subprocess.TimeoutExpired as e:
                log("Deploy script timed out after 120 seconds.")
                log(f"Timeout exception: {e}")
            except Exception as e:
                log(f"Error running deploy script: {e}")
                import traceback
                log(f"Traceback: {traceback.format_exc()}")
    else:
        log(f"Skipping Prefect deployment because RUN_PREFECT_DEPLOY={run_prefect_deploy}.")
    
    # Wait for worker to finish (if worker was started)
    if start_prefect_worker == "1" and WORKER_PROCESS:
        log("Deployment completed. Waiting for Prefect worker to finish...")
        try:
            WORKER_PROCESS.wait()
        except KeyboardInterrupt:
            signal_handler(signal.SIGTERM, None)
        except Exception as e:
            log(f"Error waiting for worker: {e}")
    else:
        log(f"Prefect worker disabled (START_PREFECT_WORKER={start_prefect_worker}). Container will remain running.")
        # Keep container running
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            signal_handler(signal.SIGTERM, None)

if __name__ == "__main__":
    main()



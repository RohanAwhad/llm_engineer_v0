import subprocess

def run_bash_command(container_name, command):
    # Construct the command
    cmd = f"docker exec {container_name} sh -c '{command}'"

    # Execute the command and return the result
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Check if the command was successful
    if result.returncode == 0:
        return result.stdout
    else:
        return f"Error: {result.stderr}. Out: {result.stdout}"

# Call the function with a test
print(run_bash_command('hello-world', 'python hello_world.py'))

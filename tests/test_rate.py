import subprocess


# TEST PARAMS
concurrent_requests = "1000"  # Number of concurrent requests
total_requests = "10000"  # Total number of requests to send

# Command to run the jordi/ab image under the 'ray-cluster' network
docker_cmd = [
    "docker", "run", "--rm",
    "--network", "ray-cluster",
    "jordi/ab"
]

docker_cmd += [
    "-n", total_requests,  # Total number of requests
    "-c",concurrent_requests,   # Number of concurrent requests
    "http://ray-head:8000/api/{slug}"  # URL to test
]


######### ALGORUNNER SERVICE TEST #########
# Service slug to test
_test_cmd = docker_cmd.copy()
_test_cmd[-1] = _test_cmd[-1].format(slug="algorunner/status")
print(
    f"Starting load test algorunner using Docker with the following command: {_test_cmd}\n"
)

# Run the command
result = subprocess.run(_test_cmd, capture_output=True, text=True)

# Print the results
print("STDOUT:\n", result.stdout)
print("STDERR:\n", result.stderr)
print("###############################################\n")

######### SCREENER SERVICE TEST #########
# Service slug to test
_test_cmd = docker_cmd.copy()
_test_cmd[-1] = _test_cmd[-1].format(slug="screener/status")
print(
    f"Starting load test screener using Docker with the following command: {_test_cmd}\n"
)
# Run the command
result = subprocess.run(_test_cmd, capture_output=True, text=True)

# Print the results
print("STDOUT:\n", result.stdout)
print("STDERR:\n", result.stderr)
print("###############################################\n")

######### TICKSCRAWLER SERVICE TEST #########
# Service slug to test
_test_cmd = docker_cmd.copy()
_test_cmd[-1] = _test_cmd[-1].format(slug="tickscrawler/status")
print(
    f"Starting load test tickscrawler using Docker with the following command: {_test_cmd}\n"
)
# Run the command
result = subprocess.run(_test_cmd, capture_output=True, text=True)

# Print the results
print("STDOUT:\n", result.stdout)
print("STDERR:\n", result.stderr)
print("###############################################\n")
# End of the test script
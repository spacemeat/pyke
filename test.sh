# run the unit tests
python3 -m unittest discover -s tests
NL=$'\n'

run_demo() {
	local demo_path="demos/$1"
	local result="$2"
	echo -n "running $demo_path... "
	output="$(pyke -m $demo_path -v0 cbd build run)"

	if [ $? -eq 0 ]; then
		output="$(echo "$output" | tr -d '\r')"
		if [ "$output" = "$result" ]; then
			echo "match"
			return 0
		else
			echo "mismatch"
			echo "expected:${NL}'${result}'"
			echo "received:${NL}'${output}'"
			return 1
		fi
	else
		echo "command failed"
		return 1
	fi
}

run_demo "custom_phase/make.py" "total: 11111"
run_demo "diamond_deps/make.py" "total: 11111${NL}total: 11111"
run_demo "multi_make/simple_0.py" "total: 11111"
run_demo "multi_make/simple_1.py" "total: 11111"
run_demo "multi_shared_objects/make.py" "255"
run_demo "simple_app/make.py" "total: 111"
run_demo "simple_lib/make.py" "total: 111"
run_demo "simple_so/make.py" "total: 111"

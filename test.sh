if [ $# == 1 ] ; then
	echo "Running test/test_$1.py"
	python3 -m unittest test/test_$1.py
else
	echo "Running test/test_*.py"
	python3 -m unittest test/test_*.py
fi


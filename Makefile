.PHONY: install run test package clean

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run:
	.venv/bin/streamlit run app.py

test:
	.venv/bin/python -m unittest test_reconciler.py

package:
	bash package_submission.sh

clean:
	rm -rf __pycache__
	rm -f take_home_submission.zip

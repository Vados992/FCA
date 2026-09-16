.PHONY: run test validate artifacts
run:
	python -m fcea serve
test:
	python -m unittest discover -s tests -v
validate:
	python scripts/validate.py --output validation-output
artifacts:
	python scripts/generate_artifacts.py

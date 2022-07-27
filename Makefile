build:
	python setup.py sdist

test-publish:
	twine upload -r testpypi dist/*

publish:
	twine upload dist/*
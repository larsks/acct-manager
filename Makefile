all: spec/definitions.yaml

spec/definitions.yaml: acct_manager/models.py
	python -m acct_manager.schema --yaml > $@ || { rm -f $@; exit 1; }

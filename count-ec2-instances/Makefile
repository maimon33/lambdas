PYTHON_VERSION ?= 3.11
FUNCTION_NAME ?= CountEc2Instances
FREQ ?= 5Minutes

help:
	@echo "==============================================="
	@echo "COUNT EC2 INSTANCES LAMBDA COMMANDS"
	@echo "==============================================="
	@echo ""
	@echo "make run      : Test the lambda function locally"
	@echo "make deploy   : Build and deploy the lambda"
	@echo "make update   : Quick code-only update"
	@echo ""

deployment-package.zip:
	zip -r deployment-package.zip main.py requirements.txt

run:
	@python3 main.py

deploy: deployment-package.zip
	@./create-or-update-function.sh $(FUNCTION_NAME) $(FREQ)

update: deployment-package.zip
	@aws lambda update-function-code \
		--function-name $(FUNCTION_NAME) \
		--zip-file fileb://deployment-package.zip

clean:
	@rm -f deployment-package.zip

.PHONY: help run deploy update clean

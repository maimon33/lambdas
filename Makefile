PYTHON_VERSION ?= 3.11
PYTHON_SITE_PACKAGES = .virtualenv/lib/python$(PYTHON_VERSION)/site-packages

help:
	@echo "make run: runs the program as it would as a lambda function"
	@echo "make deploy: create pre-reqs + deploy the lambda function"
	@echo "make libs: install local dependencies"
	@echo "make repl: drop into a repl with dependencies"
	@echo "make init: install dependencies and run the program"

libs:
	@if [ ! -d .virtualenv ]; then virtualenv .virtualenv; fi
	@. .virtualenv/bin/activate && pip install -r requirements.txt
	
run:
	. .virtualenv/bin/activate && python3 main.py

init:
	$(MAKE) libs
	$(MAKE) run

deployment-package.zip: main.py libs
	zip deployment-package.zip main.py
	mv deployment-package.zip $(PYTHON_SITE_PACKAGES)/
	cd $(PYTHON_SITE_PACKAGES) && zip -r deployment-package.zip *
	mv $(PYTHON_SITE_PACKAGES)/deployment-package.zip .

role:
	@ # Create the IAM role if it doesn't already exist
	if ! aws iam list-roles --region us-east-1| grep "${ROLE_NAME}LambdaRole" > /dev/null; then \
	  aws iam create-role --region us-east-1 --role-name "${ROLE_NAME}LambdaRole" \
	    --assume-role-policy-document file://lambda-role-trust-policy.json; \
	fi
	@ # Create the role policy which has our authorization rules
	aws iam put-role-policy --region us-east-1 --role-name "${ROLE_NAME}LambdaRole" \
	  --policy-name "${ROLE_NAME}Policy" --policy-document file://lambda-role-policy.json

deploy:
	$(MAKE) deployment-package.zip
	@echo "Select the deployment frequency:"
	@echo "1) Daily\n2) 5Minutes\n3) 1Minute"
	@read -p "Enter number: " opt; \
	case $$opt in \
		1) echo "Selected Daily"; FREQ="Daily";; \
		2) echo "Selected 5Minutes"; FREQ="5Minutes";; \
		3) echo "Selected 1Minute"; FREQ="1Minute";; \
		*) echo "Invalid selection"; exit 1;; \
	esac; \
	./create-or-update-function.sh `basename $(PWD)` $$FREQ

repl:
	. .virtualenv/bin/activate && python3

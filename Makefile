docker_image_name ?= echoIntellect
docker_image_tag ?= v1.0.0

build:
	docker build -f deploy/Dockerfile -t $(docker_image_name):$(docker_image_tag) .

run:
	cd deploy && docker-compose -f docker-compose.yaml up -d

down:
	cd deploy && docker-compose -f docker-compose.yaml down

rm:
	@docker rmi ${docker_image_name}:${docker_image_tag} || true

reset:
	-@git pull
	-@cd deploy && docker-compose -f docker-compose.yaml down
	-@$(MAKE) build
	-@cd deploy && docker-compose -f docker-compose.yaml up -d

.PHONY: build run reset down rm
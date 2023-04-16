# Slightly better than nothing

build:
	docker buildx build -t mikewyer/demo_stack:latest .

apply:
	kubectl apply -f create-frontend.yml

up:
	kubectl create -f create-frontend.yml

down:
	kubectl delete pod demostack-frontend

cycle: down up

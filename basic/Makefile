# Slightly better than nothing

build:
	docker buildx build -t mikewyer/demo_stack:latest .

upload:
	docker tag mikewyer/demo_stack:latest europe-north1-docker.pkg.dev/lets-get-it-started-384609/demostack/frontend
	docker push europe-north1-docker.pkg.dev/lets-get-it-started-384609/demostack/frontend

apply:
	kubectl apply -f create-frontend.yml

up:
	kubectl create -f create-frontend.yml

down:
	kubectl delete pod demostack-frontend

cycle: down up

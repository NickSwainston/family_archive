REGISTRY ?= localhost:5000
BUMP ?= patch
IMAGE = $(REGISTRY)/family-archive

.PHONY: release build push

# make release [BUMP=patch|minor|major] [REGISTRY=host:port]
release:
	@git diff --quiet HEAD || (echo "Working tree not clean, commit first"; exit 1)
	uv version --bump $(BUMP)
	git commit -am "Release v$$(uv version --short)"
	git tag "v$$(uv version --short)"
	$(MAKE) push

build:
	docker build --network=host -t "$(IMAGE):$$(uv version --short)" -t "$(IMAGE):latest" .

push: build
	docker push "$(IMAGE):$$(uv version --short)"
	docker push "$(IMAGE):latest"

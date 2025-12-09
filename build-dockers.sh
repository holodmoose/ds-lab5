docker build --platform linux/amd64 -t holodome/ds-bonus:latest -f ./app/bonus/Dockerfile .
docker build --platform linux/amd64 -t holodome/ds-flights:latest -f ./app/flights/Dockerfile .
docker build --platform linux/amd64 -t holodome/ds-tickets:latest -f ./app/tickets/Dockerfile .
docker build --platform linux/amd64 -t holodome/ds-gateway:latest -f ./app/gateway/Dockerfile .

docker push holodome/ds-bonus:latest
docker push holodome/ds-flights:latest
docker push holodome/ds-tickets:latest
docker push holodome/ds-gateway:latest


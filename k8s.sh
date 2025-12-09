set -eox

# helm upgrade --install postgres oci://registry-1.docker.io/bitnamicharts/postgresql -f k8s/deploy/postgres/values.yaml --wait
helm repo add gruntwork https://helmcharts.gruntwork.io
helm repo update
helm upgrade --install flights-api gruntwork/k8s-service -f k8s/deploy/flights.yaml --wait
helm upgrade --install bonus-api gruntwork/k8s-service -f k8s/deploy/bonus.yaml --wait
helm upgrade --install tickets-api gruntwork/k8s-service -f k8s/deploy/tickets.yaml --wait
helm upgrade --install gateway gruntwork/k8s-service -f k8s/deploy/gateway.yaml --wait
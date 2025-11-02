#!/bin/bash
# Monitoreo especializado para autoscaling

echo "=== MONITOREO AVANZADO AUTOSCALING ==="
echo "Cluster: autoscale-cluster"
echo "Node Pool: autoscaling-pool"
echo "Presiona Ctrl+C para detener"
echo ""

while true; do
    clear
    echo "$(date): Estado del Autoscaling"
    echo "=========================================="
    
    # Estado del cluster autoscaler
    echo "CLUSTER AUTOSCALER:"
    kubectl get configmap cluster-autoscaler-status -n kube-system -o yaml | grep -A 10 "status:"
    
    echo ""
    echo "NODE POOLS:"
    gcloud container node-pools list --cluster=autoscale-cluster --region=us-central1
    
    echo ""
    echo "NODOS ACTUALES:"
    kubectl get nodes -o wide | grep autoscale
    
    echo ""
    echo "PODS Y SU DISTRIBUCIÓN:"
    kubectl get pods -o wide --sort-by='.spec.nodeName' | grep stress-test
    
    echo ""
    echo "EVENTOS DE ESCALADO:"
    kubectl get events --sort-by='.lastTimestamp' | grep -i "scale\|autoscal" | tail -5
    
    echo ""
    echo "RECURSOS:"
    echo "Nodos: $(kubectl get nodes | grep -c autoscale)"
    echo "Pods stress-test: $(kubectl get pods | grep -c stress-test)"
    echo "Pods pendientes: $(kubectl get pods | grep stress-test | grep -c Pending)"
    
    sleep 15
done
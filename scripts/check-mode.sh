#!/bin/bash
if [ -f /opt/ai-lab/.mode ]; then
    MODE=$(cat /opt/ai-lab/.mode)
    echo "Modalità corrente: $MODE"
    docker-compose -f /opt/ai-lab/docker-compose.yml ps
else
    echo "Nessuna modalità impostata. Esegui uno script di modalità."
fi

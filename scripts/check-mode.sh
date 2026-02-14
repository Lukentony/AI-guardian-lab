#!/bin/bash
if [ -f /opt/ai-lab/.mode ]; then
    MODE=$(cat /opt/ai-lab/.mode)
    echo "Current mode: $MODE"
    docker-compose -f /opt/ai-lab/docker-compose.yml ps
else
    echo "No mode set. Please run a mode script."
fi

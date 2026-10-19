FROM clamav/clamav@sha256:ace796369e768b34d0b5b0070d3158fa07e22b2d7d5f1e2c560baddef473acf7
USER root
RUN mkdir -p /run/asila-scanner && chown 1000:1000 /run/asila-scanner && chmod 770 /run/asila-scanner
COPY deployments/clamd.conf /etc/clamav/asila.conf
USER 1000:1000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 CMD ["clamdscan", "--config-file=/etc/clamav/asila.conf", "--ping=1"]
ENTRYPOINT ["clamd", "--foreground", "--config-file=/etc/clamav/asila.conf"]

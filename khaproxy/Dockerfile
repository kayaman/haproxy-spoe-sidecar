FROM haproxy:2.7

# Default configuration directory for HAProxy in the official image
WORKDIR /usr/local/etc/haproxy/

# Copy your custom configuration
# Note: Make sure haproxy.cfg exists in the same directory as your Dockerfile
COPY haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg

# Verify the configuration is valid
RUN /usr/local/sbin/haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg

# Expose common HAProxy ports
EXPOSE 80 443

# Start HAProxy with the configuration
CMD ["/usr/local/sbin/haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]
# Synthetic Target for KAWAL SIBER Judge Demo
# Simple nginx-based web application for security assessments

FROM nginx:1.27-alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static content
COPY html/ /usr/share/nginx/html/

# Create non-root user
RUN addgroup -g 1001 appuser && \
    adduser -u 1001 -G appuser -s /bin/sh -D appuser && \
    chown -R appuser:appuser /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx/conf.d

USER appuser

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

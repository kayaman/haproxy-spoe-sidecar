# HAProxy SPOE Sidecar for Kubernetes

A Helm chart for deploying HAProxy with SPOE (Stream Processing Offload Engine) as a sidecar in Kubernetes to capture and process HTTP requests and responses.

![HAProxy SPOE Flow](https://s3.us-east-1.amazonaws.com/assets.magj.dev/haproxy-spoe-sidecar-flow.svg)

## Overview

This project provides a complete solution for intercepting HTTP traffic in your Kubernetes applications using HAProxy's Stream Processing Offload Engine (SPOE). The sidecar pattern allows you to capture both requests and responses without modifying your application code.

The Helm chart includes:

1. HAProxy configured with SPOE module
2. SPOE agent for processing captured traffic
3. Integration with downstream processors

## Features

- **Non-blocking Interception**: Capture HTTP traffic without impacting performance
- **Complete Request/Response Capture**: Get both requests and responses for complete visibility
- **Kubernetes Integration**: Designed to work as a sidecar in Kubernetes pods
- **Flexible Configuration**: Highly configurable through Helm values
- **Downstream Processing**: Forward traffic copies to external systems
- **High Performance**: Minimal overhead on your application traffic

## Requirements

- Kubernetes 1.16+
- Helm 3.0+
- HAProxy 2.4+ (included in the chart)
- Python 3.6+ (for SPOE agent)
- A downstream processor for event collection (optional, see [HTTP Event Processor](https://yourusername.github.io/http-event-processor/))

## Installation

### Using Helm (Recommended)

1. Add the HAProxy SPOE Sidecar Helm repository:

   ```bash
   helm repo add haproxy-spoe https://yourusername.github.io/haproxy-spoe/
   helm repo update
   ```

2. Install the chart:

   ```bash
   helm install haproxy-sidecar haproxy-spoe/haproxy-spoe
   ```

3. Customize installation with your own values:
   ```bash
   helm install haproxy-sidecar haproxy-spoe/haproxy-spoe -f my-values.yaml
   ```

### Configuration Options

The following table lists the configurable parameters of the HAProxy SPOE Sidecar chart and their default values:

| Parameter                      | Description            | Default                                 |
| ------------------------------ | ---------------------- | --------------------------------------- |
| `application.name`             | Application name       | `myapp`                                 |
| `application.image.repository` | Application image      | `your-application-image`                |
| `application.image.tag`        | Application image tag  | `latest`                                |
| `application.port`             | Application port       | `8000`                                  |
| `haproxy.image.repository`     | HAProxy image          | `haproxy`                               |
| `haproxy.image.tag`            | HAProxy image tag      | `2.7`                                   |
| `haproxy.port`                 | HAProxy listening port | `8080`                                  |
| `haproxy.spoe.enabled`         | Enable SPOE            | `true`                                  |
| `haproxy.spoe.bufferSize`      | SPOE buffer size       | `16384`                                 |
| `spoeAgent.enabled`            | Enable SPOE agent      | `true`                                  |
| `spoeAgent.image.repository`   | SPOE agent image       | `python`                                |
| `spoeAgent.image.tag`          | SPOE agent image tag   | `3.9-slim`                              |
| `spoeAgent.port`               | SPOE agent port        | `9000`                                  |
| `spoeAgent.downstream.url`     | Downstream service URL | `http://log-processor:8080/http-events` |

## How It Works

The HAProxy SPOE Sidecar implements the following flow:

1. Client sends an HTTP request to HAProxy
2. HAProxy triggers the `on-frontend-http-request` SPOE event
3. HAProxy sends the request details to the SPOE Agent
4. SPOE Agent forwards the request data to the Event Processor
5. HAProxy proxies the original request to the application
6. Application processes the request and returns a response to HAProxy
7. HAProxy triggers the `on-http-response` SPOE event
8. HAProxy sends the response details to the SPOE Agent
9. SPOE Agent forwards the response data to the Event Processor
10. HAProxy sends the response back to the client

This architecture ensures:

- No performance impact on the main request processing
- Complete capture of both request and response data
- Scalable processing via the SPOE agent

## Examples

### Basic Configuration

```yaml
# values.yaml
application:
  name: my-webapp
  image:
    repository: mycompany/webapp
    tag: v1.2.3
  port: 3000

haproxy:
  spoe:
    enabled: true

spoeAgent:
  downstream:
    url: 'http://event-processor.monitoring.svc.cluster.local:8080/http-events'
```

### Advanced Configuration

```yaml
# values.yaml
application:
  name: payment-api
  image:
    repository: mycompany/payment-api
    tag: v2.1.0
  port: 5000
  resources:
    limits:
      cpu: 1000m
      memory: 1Gi

haproxy:
  spoe:
    enabled: true
    bufferSize: 32768
    timeout:
      hello: 5s
      idle: 30s
      processing: 20s

spoeAgent:
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
  downstream:
    url: 'http://event-processor.monitoring.svc.cluster.local:8080/http-events'
    timeoutSeconds: 10
```

## Integration with HTTP Event Processor

This HAProxy SPOE Sidecar works best with the [HTTP Event Processor](https://yourusername.github.io/http-event-processor/) for storing and analyzing the captured traffic.

To integrate with the HTTP Event Processor:

1. Install the HTTP Event Processor:

   ```bash
   helm install event-processor http-event-processor/http-event-processor
   ```

2. Configure the SPOE agent to forward events:
   ```yaml
   # values.yaml
   spoeAgent:
     downstream:
       url: 'http://event-processor.default.svc.cluster.local:8080/http-events'
   ```

## Customization

### Custom HAProxy Configuration

You can provide custom HAProxy configuration by overriding the ConfigMap values:

```yaml
# values.yaml
haproxy:
  config:
    customConfig: |
      # Additional HAProxy configuration
      maxconn 100000
      tune.ssl.default-dh-param 2048
```

### Custom SPOE Agent Logic

You can customize the SPOE agent's processing logic:

```yaml
# values.yaml
spoeAgent:
  config:
    customProcessing: |
      # Custom processing logic
      def process_request(data):
          # Add custom fields
          data['environment'] = 'production'
          return data
```

## Troubleshooting

### Common Issues

1. **HAProxy not capturing requests**

   - Verify that SPOE is properly enabled
   - Check HAProxy logs for any configuration errors

2. **SPOE agent not receiving messages**

   - Ensure HAProxy and SPOE agent containers can communicate
   - Check SPOE agent logs for connection issues

3. **Events not reaching downstream processor**
   - Verify the downstream URL is correct
   - Check network policies allowing the connection

### Debugging

Enable debug logging for more detailed information:

```yaml
# values.yaml
haproxy:
  logLevel: debug

spoeAgent:
  logLevel: debug
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

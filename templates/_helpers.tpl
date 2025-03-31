{{/* Generate common labels */}}
{{- define "haproxy-sidecar.labels" -}}
app: {{ .Values.application.name }}
chart: {{ .Chart.Name }}-{{ .Chart.Version }}
release: {{ .Release.Name }}
heritage: {{ .Release.Service }}
{{- end -}}
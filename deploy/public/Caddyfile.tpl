{
  auto_https on
}

{{DOMAIN}} {
  encode gzip zstd
  reverse_proxy 127.0.0.1:{{PORT}}
}

{{OS_SUBDOMAIN}} {
  encode gzip zstd
  reverse_proxy 127.0.0.1:{{PORT}}
}


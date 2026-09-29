variable "channel" {
  type = string
  validation {
    condition = contains(["beta", "stable"], var.channel)
    error_message = "unsupported channel"
  }
}

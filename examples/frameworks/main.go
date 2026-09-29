package demo
import "os"
func Settle() string {
    mode := os.Getenv("SETTLEMENT_MODE")
    if mode == "live" { return "real" }
    return "dry-run"
}

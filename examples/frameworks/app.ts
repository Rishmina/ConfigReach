export function checkout() {
  const mode = process.env.PAYMENT_MODE ?? "sandbox";
  const region = process.env.REGION;
  return mode === "live" ? region : "simulated";
}

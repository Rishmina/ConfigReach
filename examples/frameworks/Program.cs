var region = Environment.GetEnvironmentVariable("REGION");
var timeout = configuration.GetValue<int>("Payment:Timeout", 30);
var enabled = await featureManager.IsEnabledAsync("CheckoutV2");

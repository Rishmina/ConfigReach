import org.springframework.beans.factory.annotation.Value;
class PaymentConfig {
  @Value("${payment.mode:sandbox}") String mode;
}

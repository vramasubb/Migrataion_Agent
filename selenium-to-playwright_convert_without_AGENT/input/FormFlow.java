public class FormFlow {
    private By email = By.name("email");
    private By submit = By.cssSelector("button[type='submit']");

    public void submit() {
        email.clear();
        email.sendKeys("user@example.test");
        submit.click();
        assertTrue(submit.isEnabled());
    }
}
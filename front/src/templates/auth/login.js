const express = require('express');
const app = express();

app.get('/auth/login.html', (req, res) => {
  // Установка заголовка Content-Security-Policy с директивой frame-ancestors 'none'
  res.setHeader('Content-Security-Policy', "frame-ancestors 'none'");

  // Отправка HTML-страницы
  res.send(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Авторизация через Telegram</title>
        <script async src="https://telegram.org/js/telegram-widget.js?5"
                data-telegram-login="ВашBotUsername"
                data-size="large"
                data-radius="10"
                data-auth-url="/auth">
        </script>
    </head>
    <body>
        <h2>Вход в систему через Telegram</h2>
        <p>Нажмите кнопку ниже, чтобы войти через свою учетную запись Telegram:</p>
        <script type="text/javascript">
            window.addEventListener('DOMContentLoaded', function () {
                TelegramWidgets.createAuthButton("telegram-login", { bot_id: "ВашBotUsername" });
            });
        </script>
    </body>
    </html>
  `);
});

app.listen(5000, () => {
  console.log('Сервер работает на порту 5000');
});
LATIN_TO_CYRILLIC = {
    'sh': 'ш', 'Sh': 'Ш', 'SH': 'Ш',
    'ch': 'ч', 'Ch': 'Ч', 'CH': 'Ч',
    'yo': 'ё', 'Yo': 'Ё', 'YO': 'Ё',
    'yu': 'ю', 'Yu': 'Ю', 'YU': 'Ю',
    'ya': 'я', 'Ya': 'Я', 'YA': 'Я',
    "o'": 'ў', "O'": 'Ў',
    "g'": 'ғ', "G'": 'Ғ',
    'ye': 'е', 'Ye': 'Е', 'YE': 'Е',
    'A': 'А', 'B': 'Б', 'V': 'В', 'G': 'Г', 'D': 'Д', 'E': 'Е', 'J': 'Ж', 'Z': 'З', 'I': 'И', 'Y': 'Й', 'K': 'К', 'L': 'Л', 'M': 'М', 'N': 'Н', 'O': 'О', 'P': 'П', 'R': 'Р', 'S': 'С', 'T': 'Т', 'U': 'У', 'F': 'Ф', 'X': 'Х', 'H': 'Ҳ', 'Q': 'Қ', 'Ts': 'Ц',
    'a': 'а', 'b': 'б', 'v': 'в', 'g': 'г', 'd': 'д', 'e': 'е', 'j': 'ж', 'z': 'з', 'i': 'и', 'y': 'й', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у', 'f': 'ф', 'x': 'х', 'h': 'ҳ', 'q': 'қ', 'ts': 'ц'
}

CYRILLIC_TO_LATIN = {
    'ш': 'sh', 'Ш': 'Sh',
    'ч': 'ch', 'Ч': 'Ch',
    'ё': 'yo', 'Ё': 'Yo',
    'ю': 'yu', 'Ю': 'Yu',
    'я': 'ya', 'Я': 'Ya',
    'ў': "o'", 'Ў': "O'",
    'ғ': "g'", 'Ғ': "G'",
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ж': 'J', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'X', 'Ҳ': 'H', 'Қ': 'Q', 'Ц': 'Ts',
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'd': 'd', 'е': 'e', 'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'x', 'ҳ': 'h', 'қ': 'q', 'ц': 'ts'
}

LANG_LABELS = {
    'uz': "🇺🇿 O'zbekcha",
    'ru': "🇷🇺 Русский",
    'en': "🇺🇸 English"
}

TEXTS = {
    'start_msg': {
        'uz': "Assalomu alaykum! Iltimos, bot tilini tanlang:",
        'ru': "Здравствуйте! Пожалуйста, выберите язык бота:",
        'en': "Hello! Please select the bot language:"
    },
    'welcome_msg': {
        'uz': "Assalomu alaykum! Quyidagi menyu orqali ishlashni boshlashingiz mumkin:",
        'ru': "Добро пожаловать! Вы можете начать работу через меню ниже:",
        'en': "Welcome! You can start working via the menu below:"
    },
    'btn_sources': { 'uz': "📡 Manbalar", 'ru': "📡 Источники", 'en': "📡 Sources" },
    'btn_my_channels': { 'uz': "📢 Kanallarim", 'ru': "📢 Мои каналы", 'en': "📢 My Channels" },
    'btn_settings': { 'uz': "⚙️ Sozlamalar", 'ru': "⚙️ Настройки", 'en': "⚙️ Settings" },
    'btn_stats': { 'uz': "📊 Statistika", 'ru': "📊 Статистика", 'en': "📊 Statistics" },
    'btn_main_menu': { 'uz': "🏠 Asosiy menyu", 'ru': "🏠 Главное меню", 'en': "🏠 Main Menu" },
    'btn_cancel': { 'uz': "❌ Bekor qilish", 'ru': "❌ Отмена", 'en': "❌ Cancel" },
    'btn_back': { 'uz': "⬅️ Orqaga", 'ru': "⬅️ Назад", 'en': "⬅️ Back" },
    'btn_add_tg': { 'uz': "📺 Telegram manba qo'shish", 'ru': "📺 Добавить Telegram источник", 'en': "📺 Add Telegram Source" },
    'btn_add_tw': { 'uz': "🐦 Twitter manba qo'shish", 'ru': "🐦 Добавить Twitter источник", 'en': "🐦 Add Twitter Source" },
    'btn_add_channel': { 'uz': "➕ Kanal qo'shish", 'ru': "➕ Добавить канал", 'en': "➕ Add Channel" },
    'btn_change_lang': { 'uz': "🌐 Tilni o'zgartirish", 'ru': "🌐 Изменить язык", 'en': "🌐 Change Language" },
    'btn_no_sig': { 'uz': "🚫 Imzosiz", 'ru': "🚫 Без подписи", 'en': "🚫 No Signature" },
    'btn_approve': { 'uz': "✅ Tasdiqlash", 'ru': "✅ Одобрить", 'en': "✅ Approve" },
    'btn_reject': { 'uz': "❌ Rad etish", 'ru': "❌ Отклонить", 'en': "❌ Reject" },
    'btn_edit': { 'uz': "📝 Tahrirlash", 'ru': "📝 Редактировать", 'en': "📝 Edit" },
    'btn_link_channel': { 'uz': "🔗 Kanalni ulash", 'ru': "🔗 Привязать kanal", 'en': "🔗 Link Channel" },
    'btn_vip': { 'uz': "💎 VIP Tarif", 'ru': "💎 VIP Тариф", 'en': "💎 VIP Tariff" },
    'btn_admin_channel': { 'uz': "🛡 Admin Kanal", 'ru': "🛡 Админ Канал", 'en': "🛡 Admin Channel" },
    'admin_channel_prompt': {
        'uz': "🛡 <b>Admin Kanalni sozlash</b>\n\nTasdiqlash xabarlari (Pending Posts) shaxsiyga kelmasligi uchun alohida kanal ochib, botni u yerda <b>ADMIN</b> qilishingiz kerak.\n\nKeyin o'sha kanalning <b>ID</b> sini yoki <b>@username</b> ini yuboring.",
        'ru': "🛡 <b>Настройка Админ Канала</b>\n\nЧтобы сообщения о подтверждении (Pending Posts) не приходили в личку, создайте отдельный канал и сделайте бота <b>АДМИНОМ</b>.\n\nЗатем отправьте <b>ID</b> или <b>@username</b> этого канала.",
        'en': "🛡 <b>Admin Channel Setup</b>\n\nTo prevent approval messages (Pending Posts) from cluttering your private chat, create a separate channel and make the bot an <b>ADMIN</b> there.\n\nThen send the <b>ID</b> or <b>@username</b> of that channel."
    },
    'admin_channel_success': {
        'uz': "✅ <b>Admin Kanal ulandi!</b>\n\nEndi barcha yangi xabarlar tasdiqlash uchun <b>{name}</b> kanaliga yuboriladi.",
        'ru': "✅ <b>Админ Канал подключен!</b>\n\nТеперь все новые сообщения для подтверждения будут отправляться в канал <b>{name}</b>.",
        'en': "✅ <b>Admin Channel linked!</b>\n\nNow all new posts for approval will be sent to the <b>{name}</b> channel."
    },
    'admin_channel_removed': {
        'uz': "❌ <b>Admin Kanal o'chirildi!</b>\n\nEndi xabarlar eski tartibda shaxsiyga keladi.",
        'ru': "❌ <b>Админ Канал удален!</b>\n\nТеперь сообщения будут приходить в личку.",
        'en': "❌ <b>Admin Channel removed!</b>\n\nNow messages will be sent to your private chat."
    },
    'btn_remove_admin_channel': { 'uz': "🗑 Kanalni o'chirish", 'ru': "🗑 Удалить канал", 'en': "🗑 Remove channel" },
    
    'limit_reached': {
        'uz': "⚠️ <b>Kunlik limitingiz tugadi!</b>\n\nSiz kuniga faqat 5 ta post tarjima qilishingiz mumkin. Cheksiz foydalanish uchun <b>VIP tarif</b> sotib oling.",
        'ru': "⚠️ <b>Ваш дневной лимит исчерпан!</b>\n\nВы можете переводить только 5 постов в день. Купите <b>VIP тариф</b> для безлимитного доступа.",
        'en': "⚠️ <b>Daily limit reached!</b>\n\nYou can only translate 5 posts per day. Purchase <b>VIP tariff</b> for unlimited access."
    },
    'vip_info': {
        'uz': "💎 <b>VIP Tarif afzalliklari:</b>\n\n- Kunlik cheksiz postlar\n- Tezkor tarjima\n- Reklamasiz foydalanish\n\n💳 <b>To'lov ma'lumotlari:</b>\nKarta: <code>8600 0000 0000 0000</code>\nEga: Falonchi Pistonchiyev\n\n📩 To'lov qilganingizdan so'ng skrinshotni shu yerga yuboring. Admin tasdiqlashi bilan VIP yoqiladi.",
        'ru': "💎 <b>Преимущества VIP Тарифа:</b>\n\n- Безлимитные посты в день\n- Быстрый перевод\n- Использование без рекламы\n\n💳 <b>Реквизиты для оплаты:</b>\nКарта: <code>8600 0000 0000 0000</code>\nВладелец: Имя Фамилия\n\n📩 После оплаты отправьте скриншот сюда. VIP будет активирован после подтверждения админом.",
        'en': "💎 <b>VIP Tariff Benefits:</b>\n\n- Unlimited daily posts\n- Faster translation\n- Ad-free usage\n\n💳 <b>Payment Details:</b>\nCard: <code>8600 0000 0000 0000</code>\nOwner: Name Surname\n\n📩 After payment, send the screenshot here. VIP will be activated after admin approval."
    },
    
    'settings_title': { 'uz': "⚙️ <b>Sozlamalar bo'limi</b>", 'ru': "⚙️ <b>Раздел настроек</b>", 'en': "⚙️ <b>Settings section</b>" },
    'lang_select_prompt': { 'uz': "🌐 <b>Iltimos, bot tilini tanlang:</b>", 'ru': "🌐 <b>Пожалуйста, выберите язык бота:</b>", 'en': "🌐 <b>Please select the bot language:</b>" },
    'lang_changed': { 'uz': "✅ <b>Bot tili o'zgartirildi:</b> {lang}", 'ru': "✅ <b>Язык бота изменен:</b> {lang}", 'en': "✅ <b>Bot language changed:</b> {lang}" },
    
    'sources_title': { 'uz': "📡 <b>Sizning manbalaringiz</b>", 'ru': "📡 <b>Ваши источники</b>", 'en': "📡 <b>Your sources</b>" },
    'sources_select': { 'uz': "Iltimos, manbani tanlang yoki yangisini qo'shing:", 'ru': "Пожалуйста, выберите источник или добавьте новый:", 'en': "Please select a source or add a new one:" },
    'add_tg_prompt': { 'uz': "📺 <b>Telegram kanal manbasini qo'shish</b>\n\nIltimos, kanalning <b>@username</b> yoki <b>ID</b> sini yuboring.\n\n<i>Misol: @mening_kanalim</i>", 'ru': "📺 <b>Добавление Telegram канала</b>\n\nПожалуйста, отправьте <b>@username</b> или <b>ID</b> канала.\n\n<i>Пример: @мой_канал</i>", 'en': "📺 <b>Adding Telegram Source</b>\n\nPlease send the <b>@username</b> or <b>ID</b> of the channel.\n\n<i>Example: @my_channel</i>" },
    'add_tw_prompt': { 'uz': "🐦 <b>Twitter manbasini qo'shish</b>\n\nIltimos, Twitter foydalanuvchi nomini yuboring.\n\n<i>Misol: elonmusk</i>", 'ru': "🐦 <b>Добавление Twitter источника</b>\n\nПожалуйста, отправьте имя пользователя Twitter.\n\n<i>Пример: elonmusk</i>", 'en': "🐦 <b>Adding Twitter Source</b>\n\nPlease send the Twitter username.\n\n<i>Example: elonmusk</i>" },
    'add_src_success': { 'uz': "Manba muvaffaqiyatli qo'shildi!", 'ru': "Источник успешно добавлен!", 'en': "Source added successfully!" },
    
    'channels_title': { 'uz': "📢 <b>Sizning kanallaringiz</b>", 'ru': "📢 <b>Ваши каналы</b>", 'en': "📢 <b>Your channels</b>" },
    'channels_empty': { 'uz': "Sizda hali kanallar yo'q. Iltimos, kanal qo'shing.", 'ru': "У вас пока нет каналов. Пожалуйста, добавьте канал.", 'en': "You don't have any channels yet. Please add a channel." },
    'add_channel_prompt': { 'uz': "➕ <b>Kanal qo'shish</b>\n\nIltimos, kanalning <b>@username</b> yoki <b>ID</b> sini yuboring.\n\n⚠️ <b>Bot kanalda admin bo'lishi shart!</b>", 'ru': "➕ <b>Добавление канала</b>\n\nПожалуйста, отправьте <b>@username</b> или <b>ID</b> канала.\n\n⚠️ <b>Бот должен быть админом в канале!</b>", 'en': "➕ <b>Adding Channel</b>\n\nPlease send the <b>@username</b> or <b>ID</b> of the channel.\n\n⚠️ <b>The bot must be an admin in the channel!</b>" },
    'alphabet_prompt': { 'uz': "🅰️ <b>Alifboni tanlang</b>\n\nPostlar ushbu alifboda yuboriladi:", 'ru': "🅰️ <b>Выберите алфавит</b>\n\nПосты будут отправляться на этом алфавите:", 'en': "🅰️ <b>Select Alphabet</b>\n\nPosts will be sent in this alphabet:" },
    'sig_prompt': { 'uz': "✍️ <b>Imzoni yuboring</b>\n\nHar bir post tagida chiqadigan matnni yozing:", 'ru': "✍️ <b>Отправьте подпись</b>\n\nВведите текст, который будет выводиться под каждым постом:", 'en': "✍️ <b>Send Signature</b>\n\nEnter the text that will be displayed under each post:" },
    'style_prompt': { 'uz': "✨ <b>Imzo uslubi</b>\n\nImzo qalin bo'lsinmi?", 'ru': "✨ <b>Стиль подписи</b>\n\nСделать подпись жирной?", 'en': "✨ <b>Signature Style</b>\n\nMake the signature bold?" },
    'spacing_prompt': { 'uz': "📏 <b>Oraliqni tanlang</b>\n\nPost va imzo orasida necha qator bo'lsin?", 'ru': "📏 <b>Выберите отступ</b>\n\nСколько строк отступа будет между постом и подписью?", 'en': "📏 <b>Select Spacing</b>\n\nHow many lines of spacing between post and signature?" },
    'add_channel_success': { 'uz': "Kanalingiz muvaffaqiyatli qo'shildi!", 'ru': "Ваш канал успешно добавлен!", 'en': "Your channel has been added successfully!" },
    'done_msg': { 'uz': "Bajarildi!", 'ru': "Готово!", 'en': "Done!" },
    
    'tg_new_post': {
        'uz': "🆕 <b>Yangi post!</b>\n\n📡 Manba: <b>{source}</b>\n📢 Kanal: <b>{channel}</b>\n🅰️ Alifbo: <b>{alpha}</b>\n\n📝 <b>Tarjima:</b>",
        'ru': "🆕 <b>Новый пост!</b>\n\n📡 Источник: <b>{source}</b>\n📢 Канал: <b>{channel}</b>\n🅰️ Алфавит: <b>{alpha}</b>\n\n📝 <b>Перевод:</b>",
        'en': "🆕 <b>New Post!</b>\n\n📡 Source: <b>{source}</b>\n📢 Channel: <b>{channel}</b>\n🅰️ Alphabet: <b>{alpha}</b>\n\n📝 <b>Translation:</b>"
    },
    'link_channel_prompt': { 'uz': "📌 <b>Kanalni tanlang</b>\n\nUshbu manbani qaysi kanalga bog'laymiz?", 'ru': "📌 <b>Выберите канал</b>\n\nК какому каналу привязать этот источник?", 'en': "📌 <b>Select Channel</b>\n\nWhich channel should this source be linked to?" }
}

def get_text(key, lang='uz', **kwargs):
    text = TEXTS.get(key, {}).get(lang, TEXTS.get(key, {}).get('uz', key))
    if kwargs:
        return text.format(**kwargs)
    return text

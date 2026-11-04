// UI chrome strings for the resident app. Mistral writes the plan message itself in the resident's language.
export type Lang = "en" | "es" | "zh" | "fil" | "vi";

type Dict = Record<string, string>;

export const T: Record<Lang, Dict> = {
  en: {
    tagline: "Your next career starts at <em>home</em>.",
    join_sub: "Free tech training for residents of participating buildings. We cover what free programs don't: child care, transit, a laptop, exam fees. Paid straight to providers, so your rent stays the same.",
    code_label: "Your building code", find_building: "Find your building", optional: "(optional)", mi_home: "mi from home", code_hint: "It's in the text message from your building.", get_started: "Get started",
    band_title: "Who pays, in order", pay_free: "Free program", pay_public: "Public aid", pay_grant: "Bridgeline grant", pay_resident: "You pay",
    band_1: "Per Scholas, TechSF, City College", band_2: "WIOA training accounts", band_3: "Only what's left, paid to providers",
    step_plan_k: "Step 2 · 5 minutes", plan_title: "Tell us in your own words.", plan_sub: "Any language. What you do now, what you'd like to do, and when you can study.",
    try_one: "Or try one:", build_plan: "Build my plan", understood: "Mistral understood you", find_programs: "Show my options",
    step_match_k: "Step 3 · Your options", match_title: "Free options first.", match_sub: "Ranked for your schedule. Each bar shows who pays.",
    best_fit: "Best fit", you_pay: "You pay", see_plan: "See my plan →", back: "Back", for_you: "for you",
    apply: "Apply in one tap", shield_title: "Benefits Shield", shield_ok: "Your rent stays the same", shield_review: "A navigator will double-check your rent",
    ai_label: "Draft from Mistral · reviewed by your navigator", how_paid: "How it's paid", milestones: "Tuition is paid in three steps", upfront: "Paid to vendors when needed",
    ms_enroll: "Enrollment", ms_complete: "Completion", ms_place: "Job or raise",
    status_title: "You're in.", status_waiting: "Your navigator is reviewing your plan. Decisions take 10 business days or less.",
    status_approved: "Approved. Your grant pays providers directly. Nothing for you to pay.", start_over: "Start over",
    j_join: "Join", j_plan: "Plan", j_match: "Match", j_apply: "Apply", j_fund: "Fund", j_complete: "Complete", j_advance: "Advance",
    reading: "Mistral is reading your story…", searching: "Searching San Francisco programs…", planning: "Building your plan…", listening: "Listening… tap again to stop",
    k_goal: "Goal", k_sched: "When you can study", k_child: "Child care", k_comp: "Computer", k_exp: "Experience", k_lang: "Language", k_work: "Work now",
    yes: "Yes", no: "No", needed: "Needed", not_needed: "Not needed", has_one: "Has one", needs_one: "Needs one",
    clarify_title: "One quick question", clarify_hint: "Mistral needs a bit more to build a plan that fits you.", answer_ph: "Type your answer…", send_answer: "Send answer", oos_kicker: "Honest answer", oos_title: "Bridgeline focuses on tech training", oos_body: "We won't change your goal to fit our programs. Here is free help for the path you described.", oos_checking: "Looking for free help for your goal…", oos_alts: "Free help for your goal", oos_none: "We don't have a listing for this goal yet. A navigator can help you find one.", oos_directory: "Browse all free help →", oos_tech: "See tech options anyway →", oos_tech_heading: "Tech options, if you're curious", on_ramp: "On-ramp", not_running: "Not running this term", on_ramp_hint: "A starter class that builds skills for the program above", no_match: "No programs matched. A navigator will reach out to plan with you.", st_available: "Available", st_confirm: "Confirm", source: "Source",
    goal_match: "Matches your goal", oos_supports: "Help while you train", oos_digital: "See computer classes →", clarify_default: "What kind of work would you like to do, and when could you study?", clarify_back: "Answer the question",
  },
  es: {
    tagline: "Tu próxima carrera empieza en <em>casa</em>.",
    join_sub: "Capacitación tecnológica gratuita para residentes de edificios participantes. Cubrimos lo que los programas gratuitos no cubren: cuidado infantil, transporte, una laptop y exámenes. Pagamos directo a los proveedores, así tu renta no cambia.",
    code_label: "Código de tu edificio", find_building: "Busca tu edificio", optional: "(opcional)", mi_home: "mi de tu casa", code_hint: "Está en el mensaje de texto de tu edificio.", get_started: "Empezar",
    band_title: "Quién paga, en orden", pay_free: "Programa gratuito", pay_public: "Ayuda pública", pay_grant: "Beca Bridgeline", pay_resident: "Tú pagas",
    band_1: "Per Scholas, TechSF, City College", band_2: "Cuentas de capacitación WIOA", band_3: "Solo lo que falta, pagado a proveedores",
    step_plan_k: "Paso 2 · 5 minutos", plan_title: "Cuéntanos con tus palabras.", plan_sub: "En cualquier idioma. Qué haces ahora, qué te gustaría hacer y cuándo puedes estudiar.",
    try_one: "O prueba uno:", build_plan: "Crear mi plan", understood: "Mistral te entendió", find_programs: "Ver mis opciones",
    step_match_k: "Paso 3 · Tus opciones", match_title: "Primero lo gratuito.", match_sub: "Ordenado según tu horario. Cada barra muestra quién paga.",
    best_fit: "Mejor opción", you_pay: "Tú pagas", see_plan: "Ver mi plan →", back: "Atrás", for_you: "para ti",
    apply: "Solicitar con un toque", shield_title: "Escudo de beneficios", shield_ok: "Tu renta no cambia", shield_review: "Un navegador revisará tu renta",
    ai_label: "Borrador de Mistral · revisado por tu navegador", how_paid: "Cómo se paga", milestones: "La matrícula se paga en tres pasos", upfront: "Pagado a proveedores cuando se necesita",
    ms_enroll: "Inscripción", ms_complete: "Graduación", ms_place: "Empleo o aumento",
    status_title: "¡Ya estás dentro!", status_waiting: "Tu navegador está revisando tu plan. La decisión toma 10 días hábiles o menos.",
    status_approved: "Aprobado. Tu beca paga directo a los proveedores. No tienes que pagar nada.", start_over: "Empezar de nuevo",
    j_join: "Unirse", j_plan: "Plan", j_match: "Opciones", j_apply: "Solicitar", j_fund: "Fondos", j_complete: "Completar", j_advance: "Avanzar",
    reading: "Mistral está leyendo tu historia…", searching: "Buscando programas en San Francisco…", planning: "Creando tu plan…", listening: "Escuchando… toca otra vez para parar",
    k_goal: "Meta", k_sched: "Cuándo puedes estudiar", k_child: "Cuidado infantil", k_comp: "Computadora", k_exp: "Experiencia", k_lang: "Idioma", k_work: "Trabajo actual",
    yes: "Sí", no: "No", needed: "Lo necesita", not_needed: "No lo necesita", has_one: "Tiene", needs_one: "Necesita una",
    clarify_title: "Una pregunta rápida", clarify_hint: "Mistral necesita un poco más para hacer un plan a tu medida.", answer_ph: "Escribe tu respuesta…", send_answer: "Enviar respuesta", oos_kicker: "Respuesta honesta", oos_title: "Bridgeline se enfoca en capacitación tecnológica", oos_body: "No vamos a cambiar tu meta para que encaje en nuestros programas. Aquí tienes ayuda gratuita para el camino que describiste.", oos_checking: "Buscando ayuda gratuita para tu meta…", oos_alts: "Ayuda gratuita para tu meta", oos_none: "Aún no tenemos un programa para esta meta. Un navegador te puede ayudar a encontrarlo.", oos_directory: "Ver toda la ayuda gratuita →", oos_tech: "Ver opciones de tecnología →", oos_tech_heading: "Opciones de tecnología, por si te interesan", on_ramp: "Primer paso", not_running: "No se ofrece este semestre", on_ramp_hint: "Una clase inicial que te prepara para el programa de arriba", no_match: "No encontramos programas. Un navegador se comunicará contigo para planear juntos.", st_available: "Disponible", st_confirm: "Confirmar", source: "Fuente",
    goal_match: "Coincide con tu meta", oos_supports: "Ayuda mientras estudias", oos_digital: "Ver clases de computación →", clarify_default: "¿Qué tipo de trabajo te gustaría hacer y cuándo podrías estudiar?", clarify_back: "Responder la pregunta",
  },
  zh: {
    tagline: "你的下一份事業，從<em>家</em>開始。",
    join_sub: "為參與計劃大樓的住戶提供免費科技培訓。我們支付免費課程不包的費用：托兒、交通、手提電腦和考試費。直接付款給服務機構，你的租金不會改變。",
    code_label: "你的大樓代碼", find_building: "搜尋你的大樓", optional: "（可選）", mi_home: "英里（離家）", code_hint: "代碼在大樓發給你的短訊裡。", get_started: "開始",
    band_title: "付款次序", pay_free: "免費課程", pay_public: "公共資助", pay_grant: "Bridgeline 補助", pay_resident: "你需付",
    band_1: "Per Scholas、TechSF、城市學院", band_2: "WIOA 培訓帳戶", band_3: "只補餘額，直接付給機構",
    step_plan_k: "第 2 步 · 5 分鐘", plan_title: "用你自己的話告訴我們。", plan_sub: "任何語言都可以。你現在做甚麼、想做甚麼、甚麼時候可以上課。",
    try_one: "或試試這些：", build_plan: "建立我的計劃", understood: "Mistral 明白你了", find_programs: "查看我的選擇",
    step_match_k: "第 3 步 · 你的選擇", match_title: "免費課程優先。", match_sub: "按你的時間排序。每條長條顯示由誰付款。",
    best_fit: "最適合", you_pay: "你需付", see_plan: "查看我的計劃 →", back: "返回", for_you: "由你支付",
    apply: "一按申請", shield_title: "福利保護", shield_ok: "你的租金不變", shield_review: "導師會再核對你的租金",
    ai_label: "Mistral 草稿 · 由你的導師審核", how_paid: "付款方式", milestones: "學費分三次支付", upfront: "需要時直接付給機構",
    ms_enroll: "入學", ms_complete: "完成課程", ms_place: "就業或加薪",
    status_title: "申請已送出。", status_waiting: "你的導師正在審核你的計劃，10 個工作天內會有決定。",
    status_approved: "已批准。補助直接付給機構，你不用付任何費用。", start_over: "重新開始",
    j_join: "加入", j_plan: "計劃", j_match: "配對", j_apply: "申請", j_fund: "資助", j_complete: "完成", j_advance: "前進",
    reading: "Mistral 正在閱讀…", searching: "正在搜尋三藩市的課程…", planning: "正在建立你的計劃…", listening: "正在聆聽…再按一次停止",
    k_goal: "目標", k_sched: "上課時間", k_child: "托兒", k_comp: "電腦", k_exp: "經驗", k_lang: "語言", k_work: "現職",
    yes: "是", no: "否", needed: "需要", not_needed: "不需要", has_one: "有", needs_one: "需要一部",
    clarify_title: "一個簡單問題", clarify_hint: "Mistral 需要多一點資料，才能為你建立合適的計劃。", answer_ph: "輸入你的回答…", send_answer: "送出回答", oos_kicker: "坦白說", oos_title: "Bridgeline 專注於科技培訓", oos_body: "我們不會為了配合課程而改變你的目標。以下是適合你所描述方向的免費資源。", oos_checking: "正在搜尋適合你目標的免費資源…", oos_alts: "適合你目標的免費資源", oos_none: "我們暫時沒有這個目標的資料。導師可以幫你尋找。", oos_directory: "瀏覽所有免費資源 →", oos_tech: "仍然查看科技課程 →", oos_tech_heading: "科技課程（供參考）", on_ramp: "入門", not_running: "本學期未開班", on_ramp_hint: "為上面的課程打好基礎的入門班", no_match: "沒有配對的課程。導師會聯絡你一起計劃。", st_available: "可申請", st_confirm: "待確認", source: "來源",
    goal_match: "符合你的目標", oos_supports: "上課期間的支援", oos_digital: "查看電腦課程 →", clarify_default: "你想做甚麼工作？甚麼時候可以上課？", clarify_back: "回答問題",
  },
  fil: {
    tagline: "Ang susunod mong karera ay nagsisimula sa <em>bahay</em>.",
    join_sub: "Libreng tech training para sa mga residente ng kalahok na gusali. Sinasagot namin ang hindi sakop ng libreng programa: child care, pamasahe, laptop at exam fee. Diretsong bayad sa provider, kaya hindi magbabago ang upa mo.",
    code_label: "Code ng gusali mo", find_building: "Hanapin ang gusali mo", optional: "(opsyonal)", mi_home: "mi mula sa bahay", code_hint: "Nasa text message mula sa gusali mo.", get_started: "Magsimula",
    band_title: "Sino ang nagbabayad, ayon sa pagkakasunod", pay_free: "Libreng programa", pay_public: "Pampublikong tulong", pay_grant: "Bridgeline grant", pay_resident: "Babayaran mo",
    band_1: "Per Scholas, TechSF, City College", band_2: "WIOA training account", band_3: "Ang natitira lang, bayad sa provider",
    step_plan_k: "Hakbang 2 · 5 minuto", plan_title: "Sabihin mo sa sarili mong salita.", plan_sub: "Kahit anong wika. Ano ang trabaho mo ngayon, ano ang gusto mo, at kailan ka puwedeng mag-aral.",
    try_one: "O subukan ang isa:", build_plan: "Gawin ang plano ko", understood: "Naintindihan ka ng Mistral", find_programs: "Ipakita ang mga opsyon",
    step_match_k: "Hakbang 3 · Mga opsyon", match_title: "Libre muna.", match_sub: "Ayon sa iskedyul mo. Ipinapakita ng bawat bar kung sino ang nagbabayad.",
    best_fit: "Pinakaangkop", you_pay: "Babayaran mo", see_plan: "Tingnan ang plano →", back: "Bumalik", for_you: "para sa iyo",
    apply: "Mag-apply sa isang tap", shield_title: "Benefits Shield", shield_ok: "Hindi magbabago ang upa mo", shield_review: "Susuriin ng navigator ang upa mo",
    ai_label: "Draft ng Mistral · sinuri ng navigator mo", how_paid: "Paano binabayaran", milestones: "Tatlong hakbang ang bayad sa tuition", upfront: "Bayad sa vendor kapag kailangan",
    ms_enroll: "Pag-enroll", ms_complete: "Pagtatapos", ms_place: "Trabaho o taas-sahod",
    status_title: "Pasok ka na.", status_waiting: "Sinusuri ng navigator ang plano mo. 10 araw ng trabaho o mas maikli ang desisyon.",
    status_approved: "Aprubado. Diretsong binabayaran ng grant ang provider. Wala kang babayaran.", start_over: "Magsimula ulit",
    j_join: "Sumali", j_plan: "Plano", j_match: "Tugma", j_apply: "Apply", j_fund: "Pondo", j_complete: "Tapusin", j_advance: "Umusad",
    reading: "Binabasa ng Mistral…", searching: "Naghahanap ng programa sa San Francisco…", planning: "Ginagawa ang plano mo…", listening: "Nakikinig… i-tap ulit para huminto",
    k_goal: "Layunin", k_sched: "Oras ng pag-aaral", k_child: "Child care", k_comp: "Computer", k_exp: "Karanasan", k_lang: "Wika", k_work: "Trabaho ngayon",
    yes: "Oo", no: "Hindi", needed: "Kailangan", not_needed: "Hindi kailangan", has_one: "Mayroon", needs_one: "Kailangan",
    clarify_title: "Isang mabilis na tanong", clarify_hint: "Kailangan ng Mistral ng kaunti pang detalye para sa planong bagay sa iyo.", answer_ph: "I-type ang sagot mo…", send_answer: "Ipadala ang sagot", oos_kicker: "Tapat na sagot", oos_title: "Nakatuon ang Bridgeline sa tech training", oos_body: "Hindi namin babaguhin ang layunin mo para lang tumugma sa aming mga programa. Narito ang libreng tulong para sa landas na sinabi mo.", oos_checking: "Naghahanap ng libreng tulong para sa layunin mo…", oos_alts: "Libreng tulong para sa layunin mo", oos_none: "Wala pa kaming listahan para sa layuning ito. Matutulungan ka ng navigator na humanap.", oos_directory: "Tingnan ang lahat ng libreng tulong →", oos_tech: "Tingnan pa rin ang tech options →", oos_tech_heading: "Mga tech option, kung interesado ka", on_ramp: "Panimula", not_running: "Hindi bukas ngayong termino", on_ramp_hint: "Panimulang klase na naghahanda sa iyo para sa programa sa itaas", no_match: "Walang tumugmang programa. Kokontakin ka ng navigator para magplano.", st_available: "Bukas", st_confirm: "Kumpirmahin", source: "Pinagmulan",
    goal_match: "Tugma sa layunin mo", oos_supports: "Tulong habang nag-aaral", oos_digital: "Tingnan ang computer classes →", clarify_default: "Anong trabaho ang gusto mo, at kailan ka puwedeng mag-aral?", clarify_back: "Sagutin ang tanong",
  },
  vi: {
    tagline: "Sự nghiệp mới của bạn bắt đầu từ <em>nhà</em>.",
    join_sub: "Đào tạo công nghệ miễn phí cho cư dân các tòa nhà tham gia. Chúng tôi chi trả những gì chương trình miễn phí không có: giữ trẻ, đi lại, máy tính xách tay, lệ phí thi. Trả thẳng cho nhà cung cấp, nên tiền thuê nhà của bạn không đổi.",
    code_label: "Mã tòa nhà của bạn", find_building: "Tìm tòa nhà của bạn", optional: "(không bắt buộc)", mi_home: "dặm từ nhà", code_hint: "Mã có trong tin nhắn từ tòa nhà.", get_started: "Bắt đầu",
    band_title: "Ai trả, theo thứ tự", pay_free: "Chương trình miễn phí", pay_public: "Hỗ trợ công", pay_grant: "Trợ cấp Bridgeline", pay_resident: "Bạn trả",
    band_1: "Per Scholas, TechSF, City College", band_2: "Tài khoản đào tạo WIOA", band_3: "Chỉ phần còn lại, trả cho nhà cung cấp",
    step_plan_k: "Bước 2 · 5 phút", plan_title: "Hãy kể bằng lời của bạn.", plan_sub: "Bất kỳ ngôn ngữ nào. Bạn đang làm gì, muốn làm gì và khi nào có thể học.",
    try_one: "Hoặc thử một câu:", build_plan: "Lập kế hoạch", understood: "Mistral đã hiểu bạn", find_programs: "Xem lựa chọn",
    step_match_k: "Bước 3 · Lựa chọn", match_title: "Ưu tiên miễn phí.", match_sub: "Xếp theo lịch của bạn. Mỗi thanh cho thấy ai trả.",
    best_fit: "Phù hợp nhất", you_pay: "Bạn trả", see_plan: "Xem kế hoạch →", back: "Quay lại", for_you: "cho bạn",
    apply: "Nộp đơn một chạm", shield_title: "Lá chắn phúc lợi", shield_ok: "Tiền thuê nhà không đổi", shield_review: "Người hướng dẫn sẽ kiểm tra lại tiền thuê",
    ai_label: "Bản nháp của Mistral · người hướng dẫn xem xét", how_paid: "Cách chi trả", milestones: "Học phí trả theo ba mốc", upfront: "Trả cho nhà cung cấp khi cần",
    ms_enroll: "Nhập học", ms_complete: "Hoàn thành", ms_place: "Có việc hoặc tăng lương",
    status_title: "Bạn đã đăng ký.", status_waiting: "Người hướng dẫn đang xem kế hoạch. Quyết định trong 10 ngày làm việc hoặc sớm hơn.",
    status_approved: "Đã duyệt. Trợ cấp trả thẳng cho nhà cung cấp. Bạn không phải trả gì.", start_over: "Làm lại",
    j_join: "Tham gia", j_plan: "Kế hoạch", j_match: "Ghép", j_apply: "Nộp đơn", j_fund: "Tài trợ", j_complete: "Hoàn thành", j_advance: "Tiến lên",
    reading: "Mistral đang đọc…", searching: "Đang tìm chương trình ở San Francisco…", planning: "Đang lập kế hoạch…", listening: "Đang nghe… chạm lần nữa để dừng",
    k_goal: "Mục tiêu", k_sched: "Thời gian học", k_child: "Giữ trẻ", k_comp: "Máy tính", k_exp: "Kinh nghiệm", k_lang: "Ngôn ngữ", k_work: "Công việc hiện tại",
    yes: "Có", no: "Không", needed: "Cần", not_needed: "Không cần", has_one: "Đã có", needs_one: "Cần một máy",
    clarify_title: "Một câu hỏi nhanh", clarify_hint: "Mistral cần thêm một chút thông tin để lập kế hoạch phù hợp với bạn.", answer_ph: "Nhập câu trả lời…", send_answer: "Gửi câu trả lời", oos_kicker: "Nói thật", oos_title: "Bridgeline tập trung vào đào tạo công nghệ", oos_body: "Chúng tôi sẽ không đổi mục tiêu của bạn cho vừa chương trình của mình. Đây là hỗ trợ miễn phí cho con đường bạn mô tả.", oos_checking: "Đang tìm hỗ trợ miễn phí cho mục tiêu của bạn…", oos_alts: "Hỗ trợ miễn phí cho mục tiêu của bạn", oos_none: "Chúng tôi chưa có thông tin cho mục tiêu này. Người hướng dẫn có thể giúp bạn tìm.", oos_directory: "Xem tất cả hỗ trợ miễn phí →", oos_tech: "Vẫn xem lựa chọn công nghệ →", oos_tech_heading: "Lựa chọn công nghệ, nếu bạn quan tâm", on_ramp: "Bước khởi đầu", not_running: "Học kỳ này không mở lớp", on_ramp_hint: "Lớp nhập môn giúp bạn chuẩn bị cho chương trình ở trên", no_match: "Không có chương trình phù hợp. Người hướng dẫn sẽ liên hệ để lập kế hoạch cùng bạn.", st_available: "Đang mở", st_confirm: "Cần xác nhận", source: "Nguồn",
    goal_match: "Đúng mục tiêu của bạn", oos_supports: "Hỗ trợ trong lúc học", oos_digital: "Xem lớp học máy tính →", clarify_default: "Bạn muốn làm công việc gì và khi nào có thể học?", clarify_back: "Trả lời câu hỏi",
  },
};

export const LANG_NAMES: Record<Lang, string> = { en: "English", es: "Español", zh: "繁體中文", fil: "Filipino", vi: "Tiếng Việt" };
export const SPEECH_LANG: Record<Lang, string> = { en: "en-US", es: "es-US", zh: "zh-TW", fil: "fil-PH", vi: "vi-VN" };
export const HTML_LANG: Record<Lang, string> = { en: "en", es: "es", zh: "zh-Hant", fil: "fil", vi: "vi" };

export function normLang(l: unknown): Lang | null {
  const s = String(l ?? "").toLowerCase();
  if (!s) return null;
  if (s.startsWith("zh") || s.includes("chinese") || s.includes("cant")) return "zh";
  if (s.startsWith("es") || s.includes("span")) return "es";
  if (s.startsWith("fil") || s.startsWith("tl") || s.includes("tagalog") || s.includes("filip")) return "fil";
  if (s.startsWith("vi") || s.includes("viet")) return "vi";
  if (s.startsWith("en")) return "en";
  return null;
}

export type TFn = (key: string) => string;
export const makeT = (lang: Lang): TFn => (k) => T[lang]?.[k] ?? T.en[k] ?? k;

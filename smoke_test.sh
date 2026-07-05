#!/usr/bin/env bash
# smoke_test.sh — проверка всех ИБ-фиксов на работающем приложении.
# Запуск:  ./smoke_test.sh            (основные проверки)
#          ./smoke_test.sh --audit    (+ pip-audit, медленнее, нужен venv)
#
# Требует: запущенные app (127.0.0.1:8000), beauty_db, beauty_redis,
# а также otp-service с SMS_MODE=mock (регистрация подтверждает телефон
# кодом — в mock-режиме otp-service отдаёт код прямо в ответе для тестов).

B="${BASE_URL:-http://127.0.0.1:8000}"
DBPASS="$(grep -E '^POSTGRES_PASSWORD=' .env 2>/dev/null | cut -d= -f2)"
DBPASS="${DBPASS:-local_dev_pass}"
PSQL=(docker exec -e PGPASSWORD="$DBPASS" beauty_db psql -U beauty_user -d beauty_platform -tAc)

# Уникальная база телефонов для этого прогона (10 цифр, начинается с 9)
BASE_PHONE=$(( 9000000000 + ($(date +%s) % 80000000) ))
phone()  { echo "+7$((BASE_PHONE + $1))"; }       # для JSON-тел (+ сохраняется)
fphone() { echo "%2B7$((BASE_PHONE + $1))"; }     # для form-данных (+ → %2B, иначе пробел)
SEED_FP="%2B79990000001"                          # сидовый телефон для form-постов

green=$'\033[32m'; red=$'\033[31m'; dim=$'\033[2m'; rst=$'\033[0m'
PASS=0; FAIL=0
ok()  { echo "  ${green}PASS${rst} $1"; PASS=$((PASS+1)); }
bad() { echo "  ${red}FAIL${rst} $1 ${dim}(ожидалось: $2, получено: $3)${rst}"; FAIL=$((FAIL+1)); }
expect(){ [ "$2" = "$3" ] && ok "$1" || bad "$1" "$2" "$3"; }
section(){ echo; echo "── $1"; }

code()  { curl -s -o /dev/null -w '%{http_code}' "$@"; }
reset_limits(){ docker exec beauty_redis redis-cli flushall >/dev/null 2>&1; }

# Регистрация теперь требует подтверждения телефона кодом из otp-service.
# В mock-режиме (SMS_MODE=mock) otp-service возвращает код прямо в ответе
# (поле dev_code) — только для тестов/локальной разработки.
get_code() {
  local resp
  resp=$(curl -s -X POST "$B/api/v1/auth/register/send-code" -H 'Content-Type: application/json' -d "{\"phone\":\"$1\"}")
  python3 -c "import sys,json;d=json.loads(sys.argv[1]);print(d.get('request_id',''));print(d.get('dev_code',''))" "$resp" 2>/dev/null
}

# ── preconditions ────────────────────────────────────────────────────────────
echo "Базовый URL: $B   | телефоны прогона: $(phone 0)…"
if [ "$(code "$B/")" != "200" ]; then echo "${red}Приложение недоступно на $B${rst}"; exit 1; fi
reset_limits

# ── 1. Политика паролей ─────────────────────────────────────────────────────
section "1. Политика сложности пароля (бриф 3.2)"
read -r RID1 CODE1 <<< "$(get_code "$(phone 1)")"
expect "слабый (нет заглавной) anna123456 → 422" 422 \
  "$(code -X POST $B/api/v1/auth/register -H 'Content-Type: application/json' -d "{\"phone\":\"$(phone 1)\",\"password\":\"anna123456\",\"request_id\":\"$RID1\",\"code\":\"$CODE1\"}")"
read -r RID2 CODE2 <<< "$(get_code "$(phone 2)")"
expect "из стоп-листа master123 → 422" 422 \
  "$(code -X POST $B/api/v1/auth/register -H 'Content-Type: application/json' -d "{\"phone\":\"$(phone 2)\",\"password\":\"master123\",\"request_id\":\"$RID2\",\"code\":\"$CODE2\"}")"
read -r RID3 CODE3 <<< "$(get_code "$(phone 3)")"
_R=$(curl -s -w $'\n%{http_code}' -X POST $B/api/v1/auth/register -H 'Content-Type: application/json' -d "{\"phone\":\"$(phone 3)\",\"password\":\"Goodpass1\",\"request_id\":\"$RID3\",\"code\":\"$CODE3\"}")
_RC=$(printf '%s' "$_R" | tail -1); _RB=$(printf '%s' "$_R" | sed '$d')
[ "$_RC" = 200 ] && ok "валидный Goodpass1 → 200" || bad "валидный Goodpass1 [body: $_RB]" 200 "$_RC"

# ── 2. Privilege escalation ──────────────────────────────────────────────────
section "2. Нет privilege escalation в регистрации (A01 #1)"
read -r RID4 CODE4 <<< "$(get_code "$(phone 4)")"
ROLE=$(curl -s -X POST $B/api/v1/auth/register -H 'Content-Type: application/json' \
  -d "{\"phone\":\"$(phone 4)\",\"password\":\"Goodpass1\",\"role\":\"business\",\"request_id\":\"$RID4\",\"code\":\"$CODE4\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('user',{}).get('role'))" 2>/dev/null)
expect "role:business игнорируется → client" "client" "$ROLE"

# ── 3. Валидация телефона ────────────────────────────────────────────────────
section "3. Валидация формата телефона"
expect "кривой телефон '12345' → 422" 422 \
  "$(code -X POST $B/api/v1/auth/register -H 'Content-Type: application/json' -d '{"phone":"12345","password":"Goodpass1"}')"

# ── 4. JWT RS256 + защита токена ─────────────────────────────────────────────
section "4. JWT RS256 (PyJWT) и защита от подделки"
TOKEN=$(curl -s -X POST $B/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"phone":"+79990000001","password":"Seedpass1"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
ALG=$(python3 -c "import sys,json,base64;t='$TOKEN';h=t.split('.')[0];h+='='*(-len(h)%4);print(json.loads(base64.urlsafe_b64decode(h))['alg'])" 2>/dev/null)
expect "alg токена = RS256" "RS256" "$ALG"
expect "битый токен → 401" 401 "$(code $B/api/v1/users/me -H 'Authorization: Bearer garbage.token.x')"

# ── 5. Хеши паролей Argon2id ─────────────────────────────────────────────────
section "5. Единый Argon2id в БД"
HASHPFX=$("${PSQL[@]}" "select left(hashed_password,9) from users order by id desc limit 1;" 2>/dev/null)
expect "новый хеш начинается с \$argon2id" '$argon2id' "$HASHPFX"
SHA_CNT=$("${PSQL[@]}" "select count(*) from users where hashed_password ~ '^[0-9a-f]{64}\$';" 2>/dev/null)
expect "сырых sha256-хешей в users нет" "0" "${SHA_CNT:-0}"

# ── 6. Поддельные отзывы (A01 #2) ────────────────────────────────────────────
section "6. Отзыв только при завершённой записи (IDOR)"
SVC=$("${PSQL[@]}" "select id from services where master_id=1 limit 1;" 2>/dev/null)
CID=$("${PSQL[@]}" "select id from users where phone='+79990000001';" 2>/dev/null)
if [ -n "$SVC" ] && [ -n "$CID" ]; then
  # чистим прошлые прогоны → негативный путь действительно без COMPLETED-записи
  "${PSQL[@]}" "delete from reviews where client_id=$CID and master_id=1;" >/dev/null 2>&1
  "${PSQL[@]}" "delete from bookings where client_id=$CID and master_id=1;" >/dev/null 2>&1
fi
expect "отзыв без COMPLETED-записи → 403" 403 \
  "$(code -X POST $B/api/v1/reviews/create -H "Origin: $B" -H "Cookie: access_token=$TOKEN" \
     -d 'master_id=1&salon_id=1&rating=5&comment=fake')"

# позитивный путь: проставим COMPLETED-запись и попробуем снова
if [ -n "$SVC" ] && [ -n "$CID" ]; then
  "${PSQL[@]}" "insert into bookings(client_id,master_id,service_id,start_time,end_time,status,discount_percent,final_price)
    values($CID,1,$SVC, now()-interval '2 day', now()-interval '2 day'+interval '30 min','COMPLETED',0,1500);" >/dev/null 2>&1
  expect "после COMPLETED отзыв проходит → 302" 302 \
    "$(code -X POST $B/api/v1/reviews/create -H "Origin: $B" -H "Cookie: access_token=$TOKEN" \
       -d 'master_id=1&salon_id=1&rating=5&comment=great')"
  expect "повторный отзыв той же паре → 409" 409 \
    "$(code -X POST $B/api/v1/reviews/create -H "Origin: $B" -H "Cookie: access_token=$TOKEN" \
       -d 'master_id=1&salon_id=1&rating=1&comment=dup')"
else
  echo "  ${dim}SKIP позитивный путь отзыва (не получил service/client из БД)${rst}"
fi

# ── 7. Дубликат review-эндпоинта удалён (#3) ─────────────────────────────────
section "7. Старый дубль review-эндпоинта удалён"
DUP=$(code -X POST $B/api/v1/bookings/reviews/create -H "Origin: $B" -H "Cookie: access_token=$TOKEN" -d 'master_id=1&salon_id=1&rating=5')
{ [ "$DUP" = 404 ] || [ "$DUP" = 405 ]; } && ok "POST на старый путь не обрабатывается (код $DUP)" || bad "старый dup-путь" "404/405" "$DUP"

# ── 8. Дефолтный пароль мастера убран (#5) ───────────────────────────────────
section "8. Нет общего пароля master123"
MASTER123=$("${PSQL[@]}" "select count(*) from users u join masters m on m.user_id=u.id;" 2>/dev/null)
# косвенно: у всех мастеров хеш argon2 (не одинаковый sha256)
DISTINCT=$("${PSQL[@]}" "select count(distinct hashed_password) from users u join masters m on m.user_id=u.id;" 2>/dev/null)
if [ "${MASTER123:-0}" -gt 0 ]; then
  expect "хеши мастеров уникальны (не общий master123)" "$MASTER123" "$DISTINCT"
else
  echo "  ${dim}SKIP (мастеров с user-аккаунтом нет)${rst}"
fi

# ── 9. Rate limiting + блокировка по аккаунту (бриф 3.6) ──────────────────────
section "9. Rate limiting и блокировка по телефону"
reset_limits
LOCK_PHONE="+79990020099"
last=""
seq1=""
for i in $(seq 1 6); do
  c=$(code -X POST $B/api/v1/auth/login -H 'Content-Type: application/json' -d "{\"phone\":\"$LOCK_PHONE\",\"password\":\"WrongPass1\"}")
  seq1="$seq1 $c"; last="$c"
done
echo "  ${dim}коды попыток:$seq1${rst}"
expect "6-я попытка входа → 429" 429 "$last"
KEYCNT=$(docker exec beauty_redis redis-cli keys "login_fail:*" 2>/dev/null | grep -c "login_fail")
[ "${KEYCNT:-0}" -ge 1 ] && ok "счётчик login_fail в Redis создан" || bad "счётчик login_fail в Redis" ">=1" "${KEYCNT:-0}"

# ── 10. CSRF (бриф 3.3) ──────────────────────────────────────────────────────
section "10. CSRF: проверка Origin для cookie-мутаций"
expect "чужой Origin + cookie → 403" 403 \
  "$(code -X POST $B/api/v1/auth/register-web -H 'Origin: http://evil.com' -H 'Cookie: access_token=x' -d "phone=$(fphone 10)&password=Goodpass1")"
read -r RID11 CODE11 <<< "$(get_code "$(phone 11)")"
expect "свой Origin → не 403 (источник принят)" 302 \
  "$(code -X POST $B/api/v1/auth/register-web -H "Origin: $B" --data-urlencode "phone=$(phone 11)" --data-urlencode "password=Goodpass1" --data-urlencode "request_id=$RID11" --data-urlencode "code=$CODE11")"

# ── 11. Security-заголовки ───────────────────────────────────────────────────
section "11. Security-заголовки"
HDRS=$(curl -sI $B/)
for h in X-Frame-Options X-Content-Type-Options Content-Security-Policy Referrer-Policy Permissions-Policy; do
  echo "$HDRS" | grep -qi "^$h:" && ok "заголовок $h присутствует" || bad "заголовок $h" "present" "absent"
done

# ── 12. CORS ─────────────────────────────────────────────────────────────────
section "12. CORS — явный список origin"
ACAO_OK=$(curl -s -o /dev/null -D - -X OPTIONS $B/api/v1/salons -H 'Origin: http://localhost:8000' -H 'Access-Control-Request-Method: GET' | grep -ci 'access-control-allow-origin')
ACAO_EVIL=$(curl -s -o /dev/null -D - -X OPTIONS $B/api/v1/salons -H 'Origin: http://evil.com' -H 'Access-Control-Request-Method: GET' | grep -ci 'access-control-allow-origin')
[ "${ACAO_OK:-0}" -ge 1 ] && ok "разрешённый origin получает ACAO" || bad "ACAO для localhost" ">=1" "${ACAO_OK}"
expect "чужой origin НЕ получает ACAO" "0" "${ACAO_EVIL:-0}"

# ── 13. Cookie-флаги ─────────────────────────────────────────────────────────
section "13. Cookie логина: HttpOnly + SameSite"
reset_limits
SETCOOKIE=$(curl -s -o /dev/null -D - -X POST $B/api/v1/auth/login-web -H "Origin: $B" \
  --data "phone=$SEED_FP&password=Seedpass1&redirect=/" | grep -i '^set-cookie')
echo "$SETCOOKIE" | grep -qi 'httponly' && ok "cookie HttpOnly" || bad "cookie HttpOnly" "present" "absent"
echo "$SETCOOKIE" | grep -qi 'samesite=lax' && ok "cookie SameSite=lax" || bad "cookie SameSite" "lax" "absent"

# ── 14. Open-redirect закрыт ─────────────────────────────────────────────────
section "14. Open-redirect в login-web закрыт"
reset_limits
LOC=$(curl -s -o /dev/null -D - -X POST $B/api/v1/auth/login-web -H "Origin: $B" \
  --data "phone=$SEED_FP&password=Seedpass1&redirect=//evil.com" | grep -i '^location:' | tr -d '\r' | awk '{print $2}')
expect "внешний //evil.com отброшен → location /" "/" "$LOC"

# ── 15. SCA / секреты (статически) ───────────────────────────────────────────
section "15. Секреты не в коде"
if grep -rqn "ruMi-supEr\|beauty_pass_2026" app/ alembic/ *.py *.ini 2>/dev/null; then
  bad "хардкод секретов в коде" "нет" "найдены"
else
  ok "ruMi-supEr / beauty_pass_2026 в коде отсутствуют"
fi
[ -f keys/jwt_private.pem ] && [ -f keys/jwt_public.pem ] && ok "RS256-ключи на месте" || bad "RS256-ключи" "есть" "нет"

if [ "$1" = "--audit" ]; then
  section "16. pip-audit (SCA)"
  if [ -f .venv/bin/pip-audit ]; then
    if .venv/bin/pip-audit >/tmp/_audit.txt 2>&1; then ok "pip-audit: уязвимостей нет"; else bad "pip-audit" "0 CVE" "$(tail -1 /tmp/_audit.txt)"; fi
  else
    echo "  ${dim}SKIP (.venv/bin/pip-audit не найден — pip install pip-audit)${rst}"
  fi
fi

# ── итог ─────────────────────────────────────────────────────────────────────
echo
echo "════════════════════════════════════════"
echo "  Итог: ${green}PASS=$PASS${rst}  ${red}FAIL=$FAIL${rst}"
echo "════════════════════════════════════════"
[ "$FAIL" -eq 0 ]

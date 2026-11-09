/**
 * Cartero de Flip PropUp (Google Apps Script).
 * El robot de GitHub le manda el resumen y este script lo envía con el Gmail de quien lo publicó.
 *
 * Cómo se publica (una sola vez, en script.google.com):
 *  1. Nuevo proyecto → pegá este código → cambiá CLAVE por una palabra larga al azar.
 *  2. Implementar → Nueva implementación → tipo "Aplicación web".
 *     Ejecutar como: Yo · Quién tiene acceso: Cualquier persona → Implementar → autorizar.
 *  3. Copiá la URL que termina en /exec y en GitHub creá el secret EMAIL_WEBHOOK con:
 *     https://script.google.com/macros/s/.../exec?clave=LA_MISMA_CLAVE
 */
const CLAVE = 'CAMBIAR_POR_UNA_CLAVE_LARGA';

function doPost(e) {
  const salida = (obj) => ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
  try {
    if (!e || !e.parameter || e.parameter.clave !== CLAVE) return salida({ ok: false, error: 'clave incorrecta' });
    const d = JSON.parse(e.postData.contents);
    const para = (d.para || []).filter(String).join(',');
    if (!para) return salida({ ok: false, error: 'sin destinatarios' });
    MailApp.sendEmail({ to: para, subject: d.asunto || 'Flip PropUp', htmlBody: d.html || '', body: d.texto || '', name: 'Flip PropUp' });
    return salida({ ok: true, cuota: MailApp.getRemainingDailyQuota() });
  } catch (err) {
    return salida({ ok: false, error: String(err) });
  }
}

function doGet() {
  return ContentService.createTextOutput('Cartero de Flip PropUp funcionando.');
}

/** Para probar desde el editor (Ejecutar → probar): manda un email a tu cuenta. */
function probar() {
  MailApp.sendEmail(Session.getActiveUser().getEmail(), 'Flip PropUp · prueba del cartero', 'Si te llegó, el cartero funciona.');
}

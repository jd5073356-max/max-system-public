/**
 * Script: formatVideoFilename.js
 * Descripción: Genera nombres de archivos formateados para videos de YouTube
 * Autor: MAX + RuFlo Swarm
 * Fecha: 2026-03-30
 */

/**
 * Formatea un título de video en nombre de archivo válido
 * @param {string} title - Título original del video
 * @returns {string} - Nombre de archivo formateado: YYYY-MM-DD-titulo-limpio
 */
function formatVideoFilename(title) {
  // Validar entrada
  if (!title || typeof title !== 'string') {
    throw new Error('El título debe ser un string no vacío');
  }

  // Obtener fecha actual en formato YYYY-MM-DD
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const dateStr = `${year}-${month}-${day}`;

  // Limpiar el título
  const cleanTitle = title
    .toLowerCase()                          // Convertir a minúsculas
    .normalize('NFD')                       // Separar acentos
    .replace(/[\u0300-\u036f]/g, '')         // Eliminar acentos
    .replace(/[^a-z0-9\s]/g, '')            // Eliminar caracteres especiales (conserva letras, números, espacios)
    .trim()                                 // Eliminar espacios al inicio/final
    .replace(/\s+/g, '-');                  // Reemplazar espacios por guiones

  // Manejar caso de título vacío después de limpiar
  if (cleanTitle.length === 0) {
    return `${dateStr}-untitled`;
  }

  // Limitar longitud (máximo 50 caracteres para el título)
  const maxTitleLength = 50;
  const truncatedTitle = cleanTitle.length > maxTitleLength
    ? cleanTitle.substring(0, maxTitleLength)
    : cleanTitle;

  return `${dateStr}-${truncatedTitle}`;
}

// ============ EJEMPLOS DE USO ============

console.log('=== Ejemplos de formatVideoFilename ===\n');

const ejemplos = [
  "Mi Primer Video de YouTube!!",
  "CÓMO ganar DINERO con n8n 🚀",
  "Tutorial: Automatización 2024 (Parte 1)",
  "   Espacios al inicio y final   ",
  "¡¡Símbolos raros!!! @#$%^&*()",
  "Video con números 123 y texto",
  "a".repeat(100), // Título muy largo
];

ejemplos.forEach((titulo, index) => {
  const resultado = formatVideoFilename(titulo);
  console.log(`${index + 1}. "${titulo.substring(0, 40)}${titulo.length > 40 ? '...' : ''}"`);
  console.log(`   → ${resultado}.mp4\n`);
});

// ============ TESTS SIMPLE ============

console.log('=== Tests Automatizados ===\n');

function test(descripcion, prueba) {
  try {
    const resultado = prueba();
    console.log(`✅ ${descripcion}`);
    return true;
  } catch (error) {
    console.log(`❌ ${descripcion}: ${error.message}`);
    return false;
  }
}

let passed = 0;
let total = 0;

// Test 1: Formato básico
total++;
if (test('Formato básico con espacios', () => {
  const result = formatVideoFilename("Hola Mundo");
  if (!result.includes('hola-mundo')) throw new Error('No convirtió correctamente');
})) passed++;

// Test 2: Mayúsculas a minúsculas
total++;
if (test('Conversión de mayúsculas', () => {
  const result = formatVideoFilename("MAYUSCULAS");
  if (result !== result.toLowerCase()) throw new Error('No convirtió a minúsculas');
})) passed++;

// Test 3: Caracteres especiales eliminados
total++;
if (test('Eliminación de caracteres especiales', () => {
  const result = formatVideoFilename("Hola!@#$%^&*()Mundo");
  if (result.includes('!')) throw new Error('No eliminó caracteres especiales');
})) passed++;

// Test 4: Formato de fecha incluido
total++;
if (test('Inclusión de fecha', () => {
  const result = formatVideoFilename("Test");
  const regex = /^\d{4}-\d{2}-\d{2}-/;
  if (!regex.test(result)) throw new Error('No incluyó fecha correcta');
})) passed++;

// Test 5: Manejo de título vacío
total++;
if (test('Manejo de título vacío después de limpiar', () => {
  const result = formatVideoFilename("!@#$%");
  if (!result.includes('untitled')) throw new Error('No manejó título vacío');
})) passed++;

// Test 6: Truncamiento de títulos largos
total++;
if (test('Truncamiento de títulos largos', () => {
  const result = formatVideoFilename("a".repeat(100));
  const titlePart = result.split('-').slice(3).join('-');
  if (titlePart.length > 50) throw new Error('No truncó el título');
})) passed++;

// Test 7: Error en entrada inválida
total++;
if (test('Error en entrada inválida', () => {
  try {
    formatVideoFilename(null);
    throw new Error('Debería haber lanzado error');
  } catch (e) {
    if (!e.message.includes('título')) throw new Error('Mensaje de error incorrecto');
  }
})) passed++;

console.log(`\n=== Resultados: ${passed}/${total} tests pasados ===`);

// Exportar para uso en otros módulos (Node.js)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { formatVideoFilename };
}

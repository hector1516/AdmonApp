import Dexie from 'dexie';

// IndexedDB offline estilo Field: caché de cotizaciones/partidas/clientes
// + outbox syncQueue. Folios reales (int) conviven con pendientes locales:
// - cotizaciones: PK idLocal (srv-{folio} en servidor, uuid en pendiente),
//   índice folio + synced.
// - partidas: folioKey = folio (int) o idLocal del padre pendiente.
// - syncQueue: ++id, entity, action, idLocal, timestamp (+payload, retries).
const db = new Dexie('AdmonDB');

db.version(1).stores({
	cotizaciones: 'idLocal, folio, synced',
	partidas: '++id, folioKey, synced',
	clientes: 'id_cliente',
	syncQueue: '++id, entity, action, idLocal, timestamp'
});

// v2: caché offline de ECCSA Legends (score, ranking, winners, avatar, etc.)
// Espejo de legendsCache en fieldDb — clave 'id' del item cacheado.
db.version(2).stores({
	legendsCache: 'id, ts'
});

// v3: caché offline GENÉRICA de lecturas GET por path de API (`/api/...`).
// Alimentada por api.get (red primero, luego guarda) y por el prefetch de
// arranque que precarga los últimos 10 registros + detalles de cada módulo.
db.version(3).stores({
	offlineCache: 'key, ts'
});

export default db;

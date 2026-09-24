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

export default db;

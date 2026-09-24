// Lógica compartida del módulo Cotizaciones (réplica exacta HUB).
// Fórmulas: venta_unit = compra*(1+factor); total_item = venta_unit*cant+flete;
// subtotal = Σ; iva = subtotal*0.16; total = subtotal+iva. Folio: CM00001.

export function folioFmt(folio) {
	const n = parseInt(folio, 10);
	return Number.isFinite(n) ? `CM${String(n).padStart(5, '0')}` : String(folio ?? '');
}

export function ventaUnit(compra, factor) {
	return (parseFloat(compra) || 0) * (1 + (parseFloat(factor) || 0));
}

export function totalItem(compra, factor, cant, flete) {
	return ventaUnit(compra, factor) * (parseInt(cant, 10) || 0) + (parseFloat(flete) || 0);
}

export function totales(partidas) {
	const subtotal = (partidas || []).reduce(
		(s, p) => s + totalItem(p.precio_compra, p.factor, p.cantidad, p.flete),
		0
	);
	const iva = subtotal * 0.16;
	return { subtotal, iva, total: subtotal + iva };
}

export function fmtMXN(v) {
	return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(v || 0);
}

// Mapeo de estatus igual que el HUB (map_estatus_text)
export function mapEstatus(status) {
	const s = String(status || '').trim().toUpperCase();
	if (s.includes('PENDIENTE') || s.includes('ENVIADA')) return 'COTIZACIÓN ENVIADA';
	if (s.includes('ENTREGADA') || s.includes('LISTA PARA FACTURAR')) return 'LISTA PARA FACTURAR';
	if (s.includes('PAGADA') || s.includes('FACTURADA')) return 'FACTURADA';
	return s;
}

export const COLOR_LABEL = {
	0: '⚪ COTIZACIÓN ENVIADA',
	1: '🟡 LISTA PARA FACTURAR',
	2: '🟢 FACTURADA'
};

export function uuid() {
	if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
	return `local-${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
}

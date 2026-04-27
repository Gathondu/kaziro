import { jsPDF } from 'jspdf';

const MM_MARGIN = 14;
const LINE_MM = 5.2;
const TITLE_PT = 11;
const BODY_PT = 10;

/** Renders plain text as a simple multi-page A4 PDF and triggers a browser download. */
export function downloadPlainTextAsPdf(options: {
	filename: string;
	heading: string;
	body: string;
}): void {
	const { filename, heading, body } = options;
	const trimmed = body.trim();
	const pdf = new jsPDF({ unit: 'mm', format: 'a4' });
	const pageW = pdf.internal.pageSize.getWidth();
	const pageH = pdf.internal.pageSize.getHeight();
	const maxW = pageW - MM_MARGIN * 2;
	let y = MM_MARGIN;

	pdf.setFontSize(TITLE_PT);
	const headingLines = pdf.splitTextToSize(heading, maxW);
	for (const line of headingLines) {
		if (y + LINE_MM > pageH - MM_MARGIN) {
			pdf.addPage();
			y = MM_MARGIN;
		}
		pdf.text(line, MM_MARGIN, y);
		y += LINE_MM;
	}
	y += 2;

	pdf.setFontSize(BODY_PT);
	const bodyLines = pdf.splitTextToSize(trimmed.length > 0 ? trimmed : ' ', maxW);
	for (const line of bodyLines) {
		if (y + LINE_MM > pageH - MM_MARGIN) {
			pdf.addPage();
			y = MM_MARGIN;
		}
		pdf.text(line, MM_MARGIN, y);
		y += LINE_MM;
	}

	pdf.save(filename);
}

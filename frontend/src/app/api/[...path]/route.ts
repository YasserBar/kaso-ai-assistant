import { NextRequest } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const BACKEND_BASE = process.env.BACKEND_URL ?? 'http://localhost:8000/api';
const API_SECRET = process.env.API_SECRET_KEY ?? process.env.NEXT_PUBLIC_API_KEY ?? '';

async function forward(req: NextRequest, pathname: string) {
  const url = `${BACKEND_BASE}/${pathname}${req.nextUrl.search}`;

  // Clone incoming headers but skip hop-by-hop/host and normalize keys to lowercase
  const headers: Record<string, string> = {};
  req.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (!['host', 'connection', 'accept-encoding', 'content-length'].includes(lower)) {
      headers[lower] = value;
    }
  });

  const method = req.method;

  let body: BodyInit | undefined = undefined;
  // Only forward a body for methods that are expected to carry one
  if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
    const contentType = headers['content-type']?.toLowerCase() ?? '';
    if (contentType.includes('application/json')) {
      // Ensure backend receives a proper JSON object, not a JSON string literal
      const json = await req.json();
      body = JSON.stringify(json);
      headers['content-type'] = 'application/json';
    } else {
      // Fallback: forward raw payload (e.g., form-data, binary)
      const buf = await req.arrayBuffer();
      body = buf;
      headers['content-type'] = headers['content-type'] || 'application/octet-stream';
    }
  } else {
    // Avoid misleading content-type on methods without a body (e.g., DELETE)
    delete headers['content-type'];
  }

  // Inject secret server-side
  if (API_SECRET) headers['x-api-key'] = API_SECRET;

  // For SSE endpoint, explicitly accept event stream
  if (pathname.endsWith('chat/stream')) {
    headers['accept'] = 'text/event-stream';
  }

  const res = await fetch(url, {
    method,
    headers,
    body,
  });

  // Prepare response headers and stream body back (supports SSE)
  const outHeaders = new Headers(res.headers);
  if (!outHeaders.has('Cache-Control')) outHeaders.set('Cache-Control', 'no-cache');
  if (!outHeaders.has('Connection')) outHeaders.set('Connection', 'keep-alive');

  return new Response(res.body, { status: res.status, headers: outHeaders });
}

export async function GET(req: NextRequest) {
  const pathname = req.nextUrl.pathname.replace(/^\/api\//, '');
  return forward(req, pathname);
}

export async function POST(req: NextRequest) {
  const pathname = req.nextUrl.pathname.replace(/^\/api\//, '');
  return forward(req, pathname);
}

export async function PUT(req: NextRequest) {
  const pathname = req.nextUrl.pathname.replace(/^\/api\//, '');
  return forward(req, pathname);
}

export async function PATCH(req: NextRequest) {
  const pathname = req.nextUrl.pathname.replace(/^\/api\//, '');
  return forward(req, pathname);
}

export async function DELETE(req: NextRequest) {
  const pathname = req.nextUrl.pathname.replace(/^\/api\//, '');
  return forward(req, pathname);
}
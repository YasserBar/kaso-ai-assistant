import { NextRequest } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const BACKEND_BASE = 'http://backend:8000/api';
const API_SECRET = process.env.API_SECRET_KEY ?? process.env.NEXT_PUBLIC_API_KEY ?? '';

async function forward(req: NextRequest, pathname: string) {
  const url = `${BACKEND_BASE}/${pathname}${req.nextUrl.search}`;

  // Clone incoming headers but skip hop-by-hop/host
  const headers: Record<string, string> = {};
  req.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (!['host', 'connection', 'accept-encoding'].includes(lower)) {
      headers[key] = value;
    }
  });

  // Always JSON for requests; inject secret server-side
  if (!headers['Content-Type']) headers['Content-Type'] = 'application/json';
  if (API_SECRET) headers['X-API-Key'] = API_SECRET;

  const method = req.method;

  let body: BodyInit | undefined = undefined;
  if (method !== 'GET' && method !== 'HEAD') {
    // Preserve exact payload for streaming endpoints
    const text = await req.text();
    body = text;
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
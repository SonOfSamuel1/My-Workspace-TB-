import { NextRequest, NextResponse } from 'next/server';

const YNAB_API_BASE = 'https://api.ynab.com/v1';

async function proxyToYnab(
  request: NextRequest,
  path: string,
  method: string
): Promise<NextResponse> {
  const apiKey = process.env.YNAB_API_KEY;

  if (!apiKey) {
    return NextResponse.json(
      { error: 'YNAB API key not configured' },
      { status: 500 }
    );
  }

  const url = `${YNAB_API_BASE}/${path}`;
  const searchParams = request.nextUrl.searchParams.toString();
  const fullUrl = searchParams ? `${url}?${searchParams}` : url;

  const headers: HeadersInit = {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  };

  const fetchOptions: RequestInit = {
    method,
    headers,
  };

  // Include body for PUT/POST/PATCH
  if (['PUT', 'POST', 'PATCH'].includes(method)) {
    try {
      const body = await request.json();
      fetchOptions.body = JSON.stringify(body);
    } catch {
      // No body provided
    }
  }

  try {
    const response = await fetch(fullUrl, fetchOptions);
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('YNAB API proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from YNAB API' },
      { status: 500 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyToYnab(request, path.join('/'), 'GET');
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyToYnab(request, path.join('/'), 'PUT');
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyToYnab(request, path.join('/'), 'POST');
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyToYnab(request, path.join('/'), 'PATCH');
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyToYnab(request, path.join('/'), 'DELETE');
}

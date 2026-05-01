import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// sha256("vanguardcreatives") — pre-computed, Edge runtime has no Node crypto
const TOKEN = '75bc049dceeb7043d9ec29555406af98b6f2e93b6c9c65bed6340cfe622ebd9e'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const isAuthed = request.cookies.get('vc_session')?.value === TOKEN

  if (pathname.startsWith('/api/login') || pathname.startsWith('/api/logout')) {
    return NextResponse.next()
  }
  if (!isAuthed && !pathname.startsWith('/login')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  if (isAuthed && pathname.startsWith('/login')) {
    return NextResponse.redirect(new URL('/', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
}

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..', '..')

function read(relative: string): string {
  return readFileSync(resolve(ROOT, relative), 'utf8')
}

const FORBIDDEN_IMPORTS = [
  'services/registry',
  'createMockServices',
  'lib/mock',
] as const

describe('news production path has no mock ownership', () => {
  it('the connected News route imports no mock service module', () => {
    const source = read('src/app/routes/news.tsx')
    for (const forbidden of FORBIDDEN_IMPORTS) {
      expect(source, `news.tsx must not import ${forbidden}`).not.toContain(forbidden)
    }
  })

  it('the presentational News screen imports no mock service module', () => {
    const source = read('src/screens/News.tsx')
    for (const forbidden of FORBIDDEN_IMPORTS) {
      expect(source, `News.tsx must not import ${forbidden}`).not.toContain(forbidden)
    }
  })

  it('default App runtime renders News through the connected route', () => {
    const source = read('src/App.tsx')
    expect(source).toContain('ConnectedNewsRoute')
    expect(source).not.toContain("import { News } from './screens/News'")
  })

  it('the generic mock registry no longer exposes a News gateway', () => {
    const ports = read('src/services/ports.ts')
    expect(ports).not.toContain('NewsGateway')
    expect(ports).not.toContain('listNews')
    const mock = read('src/services/mock/createMockServices.ts')
    expect(mock).not.toContain('listNews')
  })

  it('the mock data module no longer exports the NEWS constant', () => {
    const mock = read('src/lib/mock.ts')
    expect(mock).not.toContain('export type NewsItem')
    expect(mock).not.toContain('export const NEWS')
  })
})

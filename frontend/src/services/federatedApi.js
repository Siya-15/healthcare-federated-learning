// Federated Portal endpoints (spec section 7): Flower metadata only.
import { http, callOrMock } from './api'
import { FEDERATED_NETWORK, FEDERATED_ROUNDS, FEDERATED_MODEL } from '../mocks/federated'

export function getNetwork(opts) {
  return callOrMock(() => http('/federated/network', opts), async () => FEDERATED_NETWORK)
}

export function getRounds(opts) {
  return callOrMock(
    () => http('/federated/rounds', opts),
    async () => ({ items: FEDERATED_ROUNDS })
  )
}

export function getModel(opts) {
  return callOrMock(() => http('/federated/model', opts), async () => FEDERATED_MODEL)
}

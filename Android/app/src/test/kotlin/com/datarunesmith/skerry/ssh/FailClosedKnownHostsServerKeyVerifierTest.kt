package com.datarunesmith.skerry.ssh

import org.apache.sshd.client.session.ClientSession
import org.junit.Test
import java.lang.reflect.Proxy
import java.net.InetSocketAddress
import java.nio.file.Files
import java.nio.file.Path
import java.security.KeyPairGenerator
import java.security.PublicKey
import java.util.concurrent.CyclicBarrier
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * Drives the verifier directly so that every enrollment reaches
 * verifyServerKey at the same moment. Each SkerrySshSession owns its own
 * verifier, so this is what concurrent first connections look like; a real
 * SSH handshake rarely lines the threads up closely enough to expose the race.
 */
class FailClosedKnownHostsServerKeyVerifierTest {

    private val keyGenerator = KeyPairGenerator.getInstance("EC").apply { initialize(256) }

    @Test
    fun `concurrent first enrollments from separate verifiers keep every pin`() {
        repeat(ROUNDS) { round ->
            val file = Files.createTempDirectory("skerry-enroll").resolve("known_hosts")
            if (round % 2 == 1) Files.createFile(file) // both missing and empty trust stores
            val hosts = (0 until HOSTS).map { InetSocketAddress("127.0.0.1", 20_000 + it) to newKey() }

            val accepted = enrollConcurrently(file, hosts)

            assertTrue(accepted.all { it }, "round $round: every first-seen key must be accepted")
            val entries = Files.readAllLines(file).filter { it.isNotBlank() }
            assertEquals(HOSTS, entries.size, "round $round: a concurrent enrollment was lost:\n$entries")
            hosts.forEach { (address, key) ->
                assertTrue(verifier(file).verifyServerKey(session(address), address, key), "pinned key for $address")
                assertFalse(
                    verifier(file).verifyServerKey(session(address), address, newKey()),
                    "replacement key for $address must be rejected",
                )
            }
        }
    }

    private fun enrollConcurrently(file: Path, hosts: List<Pair<InetSocketAddress, PublicKey>>): List<Boolean> {
        val barrier = CyclicBarrier(hosts.size)
        val executor = Executors.newFixedThreadPool(hosts.size)
        try {
            val results = hosts.map { (address, key) ->
                val verifier = verifier(file)
                executor.submit<Boolean> {
                    barrier.await(10, TimeUnit.SECONDS)
                    verifier.verifyServerKey(session(address), address, key)
                }
            }
            return results.map { it.get(30, TimeUnit.SECONDS) }
        } finally {
            executor.shutdownNow()
        }
    }

    private fun verifier(file: Path) = FailClosedKnownHostsServerKeyVerifier(file)

    private fun newKey(): PublicKey = keyGenerator.generateKeyPair().public

    /** Only the connect address is consulted when a host entry is written. */
    private fun session(address: InetSocketAddress): ClientSession =
        Proxy.newProxyInstance(javaClass.classLoader, arrayOf(ClientSession::class.java)) { _, method, _ ->
            when (method.name) {
                "getConnectAddress" -> address
                "toString" -> "test-session($address)"
                "hashCode" -> address.hashCode()
                "equals" -> false
                else -> throw UnsupportedOperationException(method.name)
            }
        } as ClientSession

    private companion object {
        const val ROUNDS = 6
        const val HOSTS = 16
    }
}

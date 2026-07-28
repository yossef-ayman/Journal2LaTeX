![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image1.jpeg){width="0.9819444444444444in"
height="0.2701388888888889in"}J. Stat. Appl. Pro. Vol. No. (20\--) 185

> Journal of Statistics Applications & Probability
>
> *An International Journal*
>
> http://dx.doi.org/10.18576/jsap/1001\--

**Modification of the Authentication in the Routing Protocols in Mobile
Ad Hoc Networks (MANETs)**

*Ali Akgül ^1,2,3,4,5,\*^,* *Ahmad K. Alomari ^6^, Mohammad A. Tashtoush
^7,8^, Adel S. Hussain^9^, Emad A. Az-Zo\'bi ^10^*

^1^Department of Electronics and Communication Engineering, Saveetha
School of Engineering, SIMATS, Chennai, Tamilnadu, India

^2^Siirt University, Art and Science Faculty, Department of Mathematics,
56100 Siirt, Turkey

^3^Department of Computer Engineering, Biruni University, 34010 Topkapı,
Istanbul, Turkey

^4^Near East University, Mathematics Research Center, Department of
Mathematics, Near East Boulevard, PC: 99138, Nicosia /Mersin 10 --
Turkey

^5^Applied Science Research Center. Applied Science Private University,
Amman, Jordan

^6^Faculty of Science and Information Technology, Jadara University,
Irbid, Jordan

^7^Department of Basic Sciences, AL-Huson University College, AL-Balqa
Applied University, AL-Salt 19117, Jordan

^8^Faculty of Education and Arts, Sohar University, Sohar 311, Oman

^9^IT Department, Amedi Technical Institutes, University of Duhok
Polytechnic, Duhok, Iraq.

^10^Department of Mathematics and Statistics, Mutah University, Mutah
P.O.Box 7, Al Karak 61710, Jordan

E_mails: <aliakgul00727@gmail.com>,
[a.alomari2@jadara.edu.jo](mailto:a.alomari2@jhadara.edu.jo),
<tashtoushzz@su.edu.om>, adel.sufyan@dpu.edu.krd,
<eaaz2006@mutah.edu.jo>

Received: 27Aug. 2025, Revised: 20 Jan. 2021, Accepted: 7 Feb. 2021.

Published online: 1 \-\--. 20\--.

**Abstract:** Mobile Ad Hoc Networks (MANETs) are a novel and emerging
technology that has a dynamic topology and is self-configuring and
self-motivated. The primary feature of an ad hoc network is that it is
not dependent on any established infrastructure because it lacks a
centralised arbiter or server. These features make it harder to provide
security services to MANETs and cause security flaws. Wireless MANETs
have several issues, including performance analysis, energy efficiency,
security, and network stability. To date, a great deal of research has
been conducted to create security strategies for MANETs. The current
strategies that aim to build a defence against different types of
attacks at different levels will be covered in this book. Researchers
therefore create several routing protocols. Wireless networks cannot
effectively employ the routing methods designed for conventional
networks. A few novel routing methods have been developed for wireless
ad hoc networks that are appropriate for the constantly evolving ad hoc
wireless environment. In this study, we proposed a technique to improve
the efficiency of routing protocols and boost node-to-node dependability
in mobile ad hoc networks (MANETs). Our system focuses on node
authentication, and we use an on-demand routing protocol, such as the
Dynamic Source Routing protocol (DSR), to implement it. This technique
relies on the hash function, secret value, and time stamp.

**Keywords:** MANETs, Routing protocols, hash function, DSR, source
node, destination node.

# 

# 1 Introduction

In recent years, we have been witnessing a tremendous growth of wireless
communication technologies. The wireless network infrastructure exhibits
significant progress, making the availability of wireless applications
increase constantly. Wireless devices, such as laptops, tablets or
smartphones, can be found everywhere, and they are all getting
strongerin what it concerns their capacities. The importance of these
gadgets in our daily lives is growing.

Wireless technologies are now popular for several reasons. Due to the
substantial decline in the cost of wireless devices, service providers
are now able to drastically lower the cost of wireless services, making
them considerably more accessible to end customers \[1\]. In emerging
markets, wireless network installation is significantly less expensive
than conventional network installation. Voice and data services may now
be offered via these networks because of significant advancements in
wireless technology. Because of the ensuing appeal, anytime, anyplace
services are very desirable to end consumers.

Wireless networks come in two varieties: The first kind is an
infrastructure-based network, which is a network with reconstructed
infrastructure consisting of wired and fixed network nodes and gateways.
Typically, these preset infrastructures are used to supply network
services. The second kind is infrastructureless (ad hoc) networks, where
an arbitrary collection of independent nodes collaborates to create a
network on the fly \[2\]. There is no prior agreement on the precise
function that each node should perform.

One of the fields of study that is expanding the quickest right now is
mobile ad hoc networks, or MANETs. High-degree node mobility and
wireless communication are combined in this novel kind of
self-organising network. Thus, even in places without an established
communication infrastructure, people and cars may be operated online.
These networks lack established infrastructure, such as base stations
and centralised administration centres, in contrast to traditional wired
networks \[3\]. The type of typology this association of nodes forms is
arbitrary. While nodes within radio range can interact directly with one
another, nodes outside of that range must employ an intermediary node or
nodes to connect in a mobile ad hoc network. In these two scenarios, a
wireless network is automatically formed by all of the nodes
participating in the communication process. Consequently, one may refer
to this kind of wireless network as a mobile ad hoc network.

This kind of flexibility makes them attractive for many fields of
application, for example, in the military field, where the network
topology may change rapidly. When deployed to combat, military forces
(such as infantry, tanks, or aircraft) that are outfitted with wireless
communication equipment are more effectively connected. In disaster
recovery activities, where the fixed or current infrastructure may not
be functioning, this kind of network is also used \[4\]. Because of
their ad hoc self-organisation, they are especially appropriate for
virtual conferences, where establishing conventional network
infrastructures is an expensive and time-consuming process.

Due to this increased applicability, security matters in the mobile ad
hoc networks must be better looked at, as the basic functions of
conventional networks (packet forwarding, routing, and network
management) are carried out by dedicated nodes. In ad hoc networks,
these functions are performed collaboratively by all the available
nodes. In these types of networks, the communication between the nodes
is done through a multi-hop system. Wireless links are used for direct
communication between the nodes that are within each other's radio
range. For the nodes that are not within each other's radio range, one
or multiple intermediate nodes are used to ensure successful
communication \[5\]. Those intermediate nodes act as routers. In mobile
ad hoc networks, as their name says, the nodes are free to join, leave
or move inside the network. Due to this dynamic topology, there is a
constant need for the routes to be updated.

As seen above, because ad hoc networks allow a great freedom of movement
for the nodes that join them, this means that the network topology has a
configuration that can change rapidly. This changing nature of the nodes
is unpredictable, as it takes place at random. This type of topology,
together with a lack of infrastructure and wireless connectivity that is
prone to error, has a considerable effect on the network because it
leads to recurrent link breakages. By adopting a completely dispersed
and self-organising character, MANET protocols must lessen the
unreliability of fundamental network functions \[6\]. Distributing
network service functionality among as many nodes as feasible prevents a
single point of attack from a security standpoint. Taking into
consideration that MANETs have unique characteristics, the mechanisms
used to secure conventional networks are more likely to be unsuitable or
cannot be adapted to fit the security needs of ad hoc networks. For this
purpose, MANETs need to be equipped with specialised mechanisms and
protocols.

It has been difficult to come up with a comprehensive general solution;
most of the solutions proposed so far focus on some particular security
vulnerabilities \[4\]. A view of the bigger picture is needed for MANETs
to be provided with efficient general solutions, i.e. we have to first
fully understand all the vulnerabilities and security risks of this type
of network. As there are still many issues to be solved regarding the
deployment of security for the routing protocols of MANETs, a lot of
investigation still needs to be conducted for the development of
appropriate solutions to these issues. At this point, the critical issue
that poses the biggest challenge in this field is that of security, so
the focus must be on the design of specialised solutions to keep these
networks safe.

In this paper, we are attempting to improve a scheme used in different
kinds of routing protocols which aim to resist different forms of
attacks like eavesdropping, man-in-the-middle attack, routing attack and
wormhole attack.

**2 Related Work**

Many articles have been written to show how the security of the routing
protocols can be amended, and most of them base their research on the
On-Demand routing protocols.

Dilli Ravilla and Chandra Shekar Reddy Putta proposed Enhancing the
Security of MANETs Using Hash Algorithms \[7\]. They implemented two
secure routing techniques, keyed-Hash Message Authentication Code HMAC
and Secure Hashing Algorithm 512 (SHA512). (HMAC-SHA512). It is
implemented to make the network more secure by preventing Denial of
Service attacks in the network in which it is used. At the price of
longer processing times at both the source and the destination, they
devised the HMAC-SHA512 to guarantee that data packets are received by
the destination exclusively and in their original form. In addition to
solutions based on cryptography, a trust-based solution is also put into
place. This solution is based on the detection of malicious nodes, which
are broadcast throughout the network and isolated to increase throughput
and packet delivery fraction at the expense of an increased end-to-end
delay. By using a unified approach to digital signatures, their
suggested protocol achieves superior results in achieving security
objectives, including message integrity and message authentication.

Preeti Sachan and Pabitra Mohan Khilar suggested using a cryptographic
authentication approach to secure the AODV routing protocol in MANET
\[8\]. They presented a technique for AODV protocol security. The
suggested approach makes advantage of the hashed message authentication
code (HMAC) feature, which offers quick message verification and
authentication for both sender and intermediary nodes. It offers quick
message verification, message authentication, and intermediate node
authentication because it doesn\'t need any asymmetric key cryptography
operations. They contrast the suggested approach with the SAODV
procedure.

The suggested approach secures packet routing and effectively guards
against impersonation, black hole, and routing information modification
attacks. Additionally, they used the network simulator tool (NS2) to
simulate and compare the suggested approach with the original AODV and
secure AODV (SAODV) protocols. Simulation findings demonstrate that the
suggested approach outperforms the original AODV protocol in the
presence of hostile nodes executing black hole attacks and reduces the
time delay and network routing burden associated with computing and
verifying security fields during the route discovery phase.

An analysis of an effective DNA-based cryptographic mechanism for a
secure routing protocol for wireless ad hoc networks. In contrast to
previous cryptographic systems, Secure Routing protocols were introduced
by E. Suresh, C. Nagaraju, and MHM. Prasad to provide security solutions
for specialised wireless ad hoc networks that require less memory and
transmission capacity \[9\]. They have studied and modelled a
heterogeneous attack that takes advantage of flaws in the current
wireless ad hoc network\'s AODV routing algorithms. In particular, the
suggested SRPAHA (Secure Routing Protocol against Heterogeneous Attacks)
protocol uses hybrid DNA-based cryptography (HDC) to create
cryptographically secure communication between the nodes. Numerous
simulation scenarios that artificially create the data sets and validate
using different factors, including Route Acquisition Time, Throughput
(or packet delivery ratio), Routing Overhead, and Average End-to-End
Delay, were used to validate the simulation findings of their work.
Additionally, compared to current security systems, the outcomes of this
study offer greater security, lower computing overhead, and improved
network performance, as well as lower communication overhead.

Michael Weeks and Gulsah Altum proposed a new approach, which they
called Efficient Secure Dynamic Source Routing (ESDSR) \[10\]. It is an
algorithm using dynamic modification of the source routing (DSR)
protocol to find selfish nodes and deal with them. Their scheme focused
on wireless ad hoc networks, and they are making a distinction between
selfish nodes and malicious nodes. The discovery of the selfish nodes is
easy because they release all external information packs to conserve
battery power. The algorithm needs a Certificate Authority, and it is
based on the amended and extended DSR protocol. A shared network key is
used to encrypt the information packets exchanged by any two nodes in
the network. The protocol does not mention the issue of an attack from
the inside. It also does not offer any solution to the exploitation of
the shared key by several insiders. It is assumed that all the nodes are
reliable at first, and they collapse due to selfish reasons instead of
an outright attempt to destroy the network.

**3 Methodology**

This research employed a structured, multi-stage methodology to design,
develop, and validate an enhanced risk assessment model tailored for
project management. The primary objective was to improve the accuracy,
adaptability, and practical applicability of risk measurement across
diverse industries.

**3 Different Attacks in MANETs**

First of all, ad hoc networks must be defended against passive attacks,
which can be done with the help of the following tools: digital
signature, authentication, encryption and access control \[11, 12\].
Another challenge is represented by the protection against active
attacks. Intrusion and the number of selfish nodes also pose a problem
that needs to be taken care of. Symmetric and asymmetric cryptography
constitute the basis of encryption and authentication. In the following
sections, we shall examine several assault types and their behavior in
the sections that follow. The experiments and the reactions of the
components to some of the attacks that have been demonstrated in real
life were observed.

**Eavesdropping (passive attack)**

The attacker snoops on the network in order to collect data, getting
access to private information regarding the topology, optimal routes and
geographic locations in the network while the information is being
routed. In this case, the attack is very hard to detect, and vital
information such as the node's private and public key, password, etc.,
can be compromised. It is much easier to conduct this type of attack in
a mobile ad hoc network than in a wired network \[11\].

**Denial of Service (DoS)**

This attack aims to make a specific node not available for service. The
entire service could be compromised if someone uses this type of attack.
Denial of Service is the outcome of tampering with network integrity,
redundancy and availability. In this type of attack, an adversary wants
to use the node\'s resources or network bandwidth by overflowing the
network with insignificant information \[11\].

**Wormhole attack**

In MANETs, it is among the most advanced and serious assaults. The
attacker can tunnel the received message, which is transmitted over a
short latency, by joining two components that are located at a
predetermined distance from one another. A compromised node from a
different part of the network receives the message through a path
located outside the network, which makes the attack very difficult to
detect, because the path through which the data is transmitted does not
belong to the real network.

**Black hole attack**

In this case, all the traffic is rerouted and lured to a compromised
node, which becomes a black hole. These malicious nodes trick all their
neighbouring nodes into attracting all the routing packets to them.
Malicious nodes might initiate black hole attacks by promoting
themselves to other nodes as having the best path to the desired
destinations, which is how they are very similar to wormhole assaults.

**Snooping attack**

Duringthistypeofattackpackets
ofthenodesareaccessedwithoutpermission.Because in MANETs, packets are
communicated hop by hop, any malicious node can capture other packets
\[12\].

**Routing attack**

Routing tables get deleted or modified by malicious nodes, causing
packet overhead and increased processing time due to the destruction of
the routing information table in ordinary nodes.

**Man-in-the-middle attack**

A rogue node positions itself between the source and the destination in
this attack. After that, all packets are captured and either dropped or
altered. MANETs are especially susceptible to this assault since they
employ hop-by-hop transmission. Cryptography and authentication are the
best defences against this assault.

**Fabrication Attack**

By injecting fault information, the rogue node creates fault routing
pathways and destroys the nodes\' routing table \[12\]. Consequently,
nodes squander network resources by sending their packets over flawed
paths. An increase in lost packets and a decrease in packet delivery
rate.

**4 Improving the authentication in the routing protocols of MANETs**

The major types of ad-hoc routing protocols are: Proactive routing
protocols: routing tables are updated through recurrent message sending.
The most important protocols of this type are: OLSR (Optimised Link
State Routing protocol) and DSDV (Destination-Sequenced Distance
Vector).

Reactive (On-Demand) routing protocols: routes are generated only when
necessary. Two of the most important protocols of this kind are: DSR
(Dynamic Source Routing protocol) and AODV (Ad hoc On-Demand Distance
Vector Routing protocol).

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image3.wmf){width="4.229166666666667in"
height="1.9791666666666667in"}

**Figure 1:** Types of ad hoc routing protocols

These protocols are differentiated by the manner in which the routing
data is updated, identified, and what kind of data each routing table
keeps. Various numbers of tables can be stored by every routing
protocol.

Multiple routing protocols for ad hoc networks were created to ensure
security and authentication between the nodes. In this paper, we propose
security schemes which can be applied to most of the routing protocols.
To apply our schemes, we use the Dynamic Source Routing protocol (DSR)
due to its popularity and frequent usage \[13\].

Our paper has been done on the verification between the nodes. Mobile ad
hoc networks that use authorised nodes are becoming more and more
available to general use and also a research topic with increased
importance over the last few years.

Mobile nodes, which may function as both senders and forwarders for
messages, make up the structure of a MANET. Our focus will be on a
unique aspect of these protocols, which is the ability to identify
routes, which helps to overcome the network\'s dynamic topology
limitation.

Mobile ad hoc networks provide two security challenges. Communication
between the nodes is made possible by the security of the routing
protocols, which is the first issue. The protection of the data that is
moving across the network along routes set by the routing protocols is
the second issue. In an ad-hoc network, there are two kinds of attacks:
passive attacks and active assaults.

Our proposed idea utilises hash functions, although digital signatures
can be used as well. To acquire strong security, the scheme of SAODV
(Security AODV: represents an AODV extension) includes algorithms that
use digital signatures and hash chains to accomplish the security on
different levels. The digital signature is attached to every node to
provide integrity and authentication for the messages concerning the
routing: RREQ, RREP and RRER. All the neighbour nodes that receive the
packet verify the digital signature. The hash chains are used to secure
the hop-count mechanism \[13, 14\].

In this scheme, we use the random number generator, besides the one-way
hash function. We use this method to improve the communication between
the nodes and to perform node authentication. The steps of this scheme
are explained in Figure 2.

In our scheme, we still use a digital signature and time to live (TTL).
Where TTL lists the number of times this message can be resent, and the
digital signature is attached to every node to provide integrity and
authentication for the messages sent between two nodes.

Parameters used:

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image4.wmf):
identity of the source node;

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image5.wmf):
identity of the destination node;

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image6.wmf):
Random number generated by source node;

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image7.wmf):
Random number generated by destination node;

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image8.wmf):
Public key of the source node;

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image9.wmf):
Public key of the destination node;

H (x): secure one-way hash function;

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image10.wmf):
Secret value.

Secret Value
(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image10.wmf))
Distribution with Confidentiality and Authentication: We can use the
public key to exchange the secret value to provide protection against
both active and passive attacks.

Diffie-Hellman Key Exchange: The Diffie-Hellman algorithm\'s efficiency
depends on the hardness of computing discrete logarithms.

Our approach is based on a practical one-way hash function. We also
deliver a theoretically stronger foundation on pseudo-random function
(PRF).

As stated before, in this scheme we use the random number generator,
besides the one-way hash function. To improve the communication between
the nodes, we use this method to perform node authentication, and we
explain it as follows:

- The source
  node![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image11.wmf)wants
  to communicate with the destination node
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image12.wmf),
  as illustrated in Figure 2.
  Node![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image11.wmf)first
  produces a nonce
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image13.wmf)
  and encrypts that value with the public key of destination node
  *E*![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image14.wmf)(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image15.wmf)).
  The source node sends it with the request message to the destination
  node![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image12.wmf).

- When the destination node receives the message from the source node,
  directly or by intermediate nodes, if it is out of the range of the
  source node, the destination node decrypts the value
  *E*![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image14.wmf)(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image16.wmf))
  using its private key to get
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image17.wmf).
  After
  that,![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image12.wmf)the
  node
  generates![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image18.wmf)
  and
  computes![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image19.wmf)
  and sends it with the time stamp
  (![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image20.wmf))
  and
  *E*![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image21.wmf)(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image22.wmf)),
  where
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image23.wmf)
  is the public key of the source node, to the source node.

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image14.wmf)

**Figure 2:** Authentication improvement in routing protocols of MANETs

- When the source node
  receives![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image32.wmf)*E*![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image21.wmf)(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image33.wmf))
  values from the destination, it verifies the time of the message by
  comparing the current time of the source node with the destination
  node's time. If the message is accepted, the source node will get
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image34.wmf)
  by decrypting
  *E*![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image21.wmf)(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image35.wmf))
  using the private key. After that, the source node looks for the
  identities of the destination node
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image36.wmf)
  , such as
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image37.wmf)the
  number of nodes in the MANETs, by computing
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image38.wmf)
  and making the following comparison
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image39.wmf).
  If the destination node passes the authentication of the source node,
  it is considered legitimate; otherwise, it is ignored. After that, the
  source node computes and sends this message to the destination node
  with the new time of the source
  (![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image40.wmf)).

<!-- -->

- When the destination gets the last value from the source node, it
  checks![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image41.wmf).
  If it is valid, the node
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image12.wmf)starts
  the authentication process by
  computing![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image42.wmf)again.
  After that, it checks if
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image43.wmf).
  For the last authentication process, the destination node computes
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image44.wmf)and
  sees if
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image45.wmf).
  Finally, the destination node produces
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image46.wmf)and
  sends it with the new time
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image47.wmf)
  to the source node.

- When the source receives the last value from the destination node, it
  starts the last verification process by checking
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image48.wmf)
  and computing
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image49.wmf)
  to see if it matches the received value
  ![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image50.wmf).

The source and destination authenticate each other. Naturally, the hash
value is authenticated together with the destination ID that is
contained as a component of the hash value.

**Case study (Example by using DSR)**

We choose the Dynamic Source routing protocol to apply our proposed
scheme with nonce and secret
value![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image51.wmf).
In this protocol, communication is started with the first RREQ message
sent by a node. This means that the first stage of the routing process
is deployed: the route discovery process. The RREQ travels with the
source's digital signature
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image52.wmf)attached.
The neighbours which receive the RREQ examine the signature of the
source and, thereupon, take a decision. To support message integrity, we
still use the one-way hash function. Destination sequence number is also
utilised in order to avoid the formation of loops and to verify if the
route is also the newest one.

We presume that the source
node![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image11.wmf)
is attempting to find a route to the destination
node![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image12.wmf).
There is a route
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf)![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image12.wmf)
that goes through intermediate
nodes![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image54.wmf)![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image55.wmf).
We still use here L: life time of the package (maximum number of hops),
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image56.wmf):
Digital signature of
node![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf),![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image57.wmf):
Hash value added by the source node to the
packet.![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image58.wmf)

The operations of our protocol will work as explained below: A RREQ is
generated by the source
node![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf),
with the time stamp of the source node, to initiate route discovery.
RREQ includes several parameters, enumerated as follows: source address,
destination address, Seq, LREQ, authentication request (auth req),
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image56.wmf)digital
signature of source, hash value
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image59.wmf)
and a routing table that includes all the intermediate nodes which find
themselves on the path
from![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf)
source
to![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image12.wmf)destination.
A message can be broadcast a limited number of times. This number is
known as the lifetime of a packet. Every broadcast automatically
decreases the lifetime number by one. If the time number reaches zero,
the packet will be dismissed. Source produces the
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image60.wmf)
output using a one-way hash function.

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image61.wmf)
= H(S, D, Seq, LREQ).

When a neighbor
of![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf),
for
example![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image54.wmf),
receives the RREQ message
with![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image62.wmf),
the first thing it does is to check
the![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image63.wmf)of![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf).
If S passes the examination and it is considered authentic, the
intermediate node
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image54.wmf)proceeds
in verifying the Seq and matches it with the one that it has stored in
its cache.
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image54.wmf)dismisses
the packet if the Seq stored is higher than the Seq received. If Seq is
equal to or higher, the node
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image54.wmf)adds
its identifier to the route list and digital signature
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image63.wmf)![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image54.wmf)
to the message and replaces the
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image61.wmf)by
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image64.wmf)
and then rebroadcasts

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image65.wmf)=
H(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image61.wmf),![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image54.wmf),
LREQ -1),
E![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image14.wmf)(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image66.wmf)).![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image58.wmf)

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image55.wmf)

**Figure 3:** Broadcasting routing request and routing replay

This procedure is similar for the next neighbour
node![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image55.wmf).
It checks both signatures of
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf),
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image67.wmf)and
after that, it verifies the sequence. When the checklist is completed,
it adds its identifier to the route list and a digital signature
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image68.wmf)
to the message, it replaces the
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image69.wmf)
by
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image70.wmf)
, and finally rebroadcasts.

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image71.wmf)=
H
(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image65.wmf),
E, LREQ-2),
E![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image14.wmf)(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image66.wmf)).![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image58.wmf)

Finally, the RREQ arrives at the destination node
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image72.wmf)with
the source's time
stamp![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image73.wmf),
which ensures the value
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image74.wmf).
After that, it checks all the signatures included in the RREQ message
and matches the Seq with the previously stored Seq in its cache. If the
examination concluded that S and the intermediate nodes are valid and
the packet is up-to-date,
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image75.wmf)
it calculates:
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image76.wmf)=
H(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image77.wmf),
LREQ-2,
H(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image78.wmf),
LREQ-1,
H(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf),![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image12.wmf),
Seq, LREQ) and confronts the value of
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image76.wmf)with
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image71.wmf).
If both values coincide, the integrity of the packet is authenticated.
Otherwise, the message is discarded. If all the parameters pass the
examination, the destination node generates a nonce
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image79.wmf)
, and then it computes
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image19.wmf).

Finally, the destination node
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image72.wmf)generates
a RREP, which it sends back
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf)on
the same route that RREQ arrived, only in reverse. Route Reply (RREP)
message also includes some parameters, enumerated as follows: Seq,
source address, destination address, route list,
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image80.wmf),
(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image20.wmf))
and
E![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image21.wmf)(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image22.wmf))
and a list with all the signatures of the intermediate nodes from source
to destination. Every intermediate node follows the same procedures as
when it receives a RREQ: checks the signature of
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image72.wmf)and
verifies Seq to establish how fresh the route is. When RREP
arrives![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf),
this checks the signatures of all the nodes in the route list and Seq.
Source
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf)computes:

H = H
(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image81.wmf),
LREQ-2, H
(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image82.wmf),
LREQ-1, H
(![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf),![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image72.wmf)![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image58.wmf),
Seq, LREQ))),

and compares with
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image83.wmf)to
verify the integrity of the route list. If the values are equal,
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf)it
accepts RREP. Otherwise, the packet is dismissed.
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf)Calculates
the values of LREQ-1 and LREQ-2 based on the route list. After that, the
source node creates a response to the destination node by generating

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image84.wmf),

![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image85.wmf).

Sending it by the same path to the destination node. In the end, the
destination verifies this value and, if it matches, the authentication
process has succeeded. After all the procedures and the examinations are
completed, a route is established from the source node
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image53.wmf)to
the destination node
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image72.wmf).

**5 Security Analysis**

In this section, we explain how we achieved the mutual authentication
between the nodes in MANETs, and then we explain how the scheme acts
with different kinds of attacks.

**Achieve Mutual Authentication**

The process of mutual authentication is obtained after the secret shared
value *k* is verified, i.e. it is the same at both ends of the
communication. Also, the destination node has to certify that the last
message received is from the source node. At this point, it is assumed
that secure communication between the source node and the destination
node has taken place. Our scheme guarantees the authentication of the
source node through the secret shared value *k*. This prevents any
compromised node from disturbing the communication process, as it will
be detected when it tries to communicate with the destination node. The
destination node will start the authentication process whenever it
receives a challenge from the source node. It is also important for the
authentication process to take place in a single session. To ensure
this, timestamps are also employed in our scheme.

**Anonymity, Untraceability and Eavesdropping**

Anonymity and untraceability can be obtained through the use of a nonce
(random numbers). The nonce must be added to each authentication request
made by either the source node or the destination node. The source is
notified that the destination is authenticated through a final hashed
message sent by the destination. This step is to keep the destination
node anonymous and untraceable. Once again, the messages must take place
in the same authentication session. To make sure of this, the use of
timestamps is again needed.

Our authentication scheme provides full protection against future
forward and backwards traceability. The adversary has no control over
nonce
values![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image86.wmf),![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image87.wmf)and
the combination
of![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image86.wmf)
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image88.wmf)
a hash function and also does not know the secret
value![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image89.wmf).
All values between the source and destination nodes will be unique in
each session and replaced after each successful session, which provides
a high level of privacy.

**Eavesdropping**

Because the communication between the source node and the destination
node is encrypted with a public key and the shared secret value is
hashed with a nonce, an eavesdropping attack is unlikely to succeed
because a malicious node cannot take part in the exchange between the
source and the destination.

**Impersonation Attack Resistance**

During the communication, all the values are hashed and XORed. This
prevents a node impersonation attack. Our scheme also proposes the use
of updated nonce, i.e. random numbers, for each communication between
the source and destination nodes, making the resistance stronger. The
result of our scheme shows that the nodes communicate with each other in
MANETs through a secure channel.

**Man-in-the-Middle Attack**

After the mutual authentication process takes place, the messages cannot
be modified by an attacker because future communication is performed and
controlled by two authenticated parties. In each new communication, the
secret value
![](G:\work\Journal2LaTeX\backend\temp\4c33ac9f-5698-4ea4-86dc-313f4d965dda\intermediate\media/media/image90.wmf)is
updated, as well as the random nonce numbers. After its authentication,
the destination is protected until the completion of the session. The
security level is also increased by the use of hash functions on the
messages.

**Denial of Service Attack (DoS)**

DoS attacks are very tricky to detect, and oftentimes, some manage to
pass undetected. The objective of the protocol is to take action against
the vulnerability presented by a DoS attack, avoiding the
desynchronization of the system. Because our scheme is enhanced with
timestamps, an active attack on a node is impossible. This is due to the
fact that the previous timestamp is always stored by the node, which
will not allow any other authentication to take place until it receives
a timestamp higher than the previous one. Due to this monotonically
increasing timestamp, an impersonation and replay attack is not
possible. In case of an attempt to use a higher fake timestamp, this
protocol is also at an advantage: the node does not update its timestamp
unless a successful authentication is performed. This prevents the
protocol from DoS attacks.

**6 Conclusion**

MANET security research is still in its infancy. The current approaches
are usually attack-oriented, identifying many security concerns first,
then either improving the current protocol or proposing a new one to
counter them.

In this paper, we present the most important attacks on the routing
protocols and how we resist these attacks in a secure way. Also, we
propose a scheme to increase the security between the nodes by enhancing
and improving the authentication and confidentiality between the nodes.
The proposed idea uses hash functions, but digital signatures can be
used. The method used the hash function and nonce (random number) with a
secret value, and we explain how our scheme works in the Dynamic Source
Routing protocol (DSR). Our solution expands the security scope and
provides more authentication services between the nodes in MANET.

***Conflicts of Interest Statement***

*The authors certify that they have NO affiliations with or involvement
in any organization or entity with any financial interest (such as
honoraria; educational grants; participation in speakers' bureaus;
membership, employment, consultancies, stock ownership, or other equity
interest; and expert testimony or patent-licensing arrangements), or
non-financial interest (such as personal or professional relationships,
affiliations, knowledge or beliefs) in the subject matter or materials
discussed in this manuscript.*

**References**

1.  M. Conti, Body, Personal and Local Ad Hoc Wireless Networks, in Book
    TheHandbook of Ad Hoc Wireless Networks (Chapter 1), CRC Press LLC,
    2003.

2.  M. S. Corson, J.P. Maker, and J.H. Cernicione, Internet-based Mobile
    Ad HocNetworking, IEEE Internet Computing, pages 63--70, July-August
    1999.

3.  Capkun, J. Hubaux, and L. Buttyan, "Mobility Helps Peer-to-Peer
    Security," IEEE Transactions on Mobile Computing, vol. 5, no. 1, pp.
    43--51, 2006.

4.  Ming-Yang Su, "A Study of Deploying Intrusion Detection Systems in
    Mobile Ad Hoc Networks", WCE 2012.

5.  Zhaohua Long, Zheng He.\"Optimization and Implementation of DSR
    Route Protocol based on Ad hocnetwork\", Wireless Communications,
    Networking and Mobile Computing, 2007.

6.  S. Capkun, L. Buttyan, and J.-P. Hubaux, "Self-Organized Public-Key
    Management for Mobile Ad Hoc Networks," IEEE Transactions on Mobile
    Computing, vol. 2, no. 1, pp. 52--64, 2003.

7.  Dilli Ravilla ,C. Shekar Reddy Putta, "Enhancing the Security of
    MANETs Using Hash Algorithms", Eleventh international
    multi-conference on information processing, 2015.

8.  P. Sachan, P. Mohan Khilar, "Securing AODV routing protocol in MANET
    based on cryptographic authentication mechanism", International
    Journal of Network Security & Its App lications (IJNSA), 2011.

9.  E.Suresh, C Nagaraju , "Analysis of Secure Routing Protocol for
    Wireless Ad hoc Networks using Efficient DNA based Cryptographic
    Mechanism", ICECCS 2015.

10. Michael Weeks, and Gulsah Altun, "Efficient, Secure, Dynamic Source
    Routing for Ad-hoc Networks", Journal of Network and Systems
    Management, Vol. 14, No. 4, December 2006 (\_c 2006) DOI:
    10.1007/s10922-006-9043-8.

11. A. Dorri , S. Reza Kamel and E. Kheyrkhah, "Security Challenge in
    Mobile Ad Hoc Networks: A Survey", International Journal of Computer
    Science & Engineering Survey, 2015.

12. Praveen Joshi, "Security issues in routing protocols in MANETs at
    network layer", WCIT-2010.

13. A. Kumar, V. K. Katiyar and K. Kumar, "Secure Routing Proposal in
    MANETS: A Review", International Journal in Foundations of Computer
    Science & Technology (IJFCST), 2016.

14. Hussain, A., Oraibi, Y., Mashikhin, Z., Jameel, A., Tashtoush, M.,
    Az-Zo'bi, E. (2025). New Software Reliability Growth Model:
    Piratical Swarm Optimization -Base Parameter Estimation in
    Environments with Uncertainty and Dependent Failures, [*Statistics,
    Optimization & Information
    Computing*](http://www.iapress.org/index.php/index), 13(1), 209-221.
